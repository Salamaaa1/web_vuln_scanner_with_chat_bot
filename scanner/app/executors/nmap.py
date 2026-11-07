import asyncio
import os
import shutil
import xml.etree.ElementTree as ET
from app.Exception.tools_exception import ToolInternalError, ToolNotFoundError
from app.executors.base import Executor

# Ports considérés comme "web" -> utilisés pour décider du pivot vers le Pipeline URL
WEB_PORTS = {80, 443, 8080, 8443}

class NmapExecutor(Executor):

    def parse(self, stdout: bytes) -> dict:
        ports = []
        host_status = "unknown"
        os_info = {}

        try:
            root = ET.fromstring(stdout.decode())
        except Exception:
            return {"host_status": host_status, "ports": ports, "os_info": os_info}

        host_el = root.find("host")
        if host_el is None:
            return {"host_status": host_status, "ports": ports, "os_info": os_info}

        # 1. Extraction du statut de l'hôte
        status_el = host_el.find("status")
        if status_el is not None:
            host_status = status_el.get("state", "unknown")

        # 2. Extraction du Fingerprinting OS
        os_el = host_el.find("os")
        if os_el is not None:
            osmatch_el = os_el.find("osmatch")
            if osmatch_el is not None:
                os_info["name"] = osmatch_el.get("name", "")
                os_info["accuracy"] = int(osmatch_el.get("accuracy", 0))
                
                osclass_el = osmatch_el.find("osclass")
                if osclass_el is not None:
                    os_info["family"] = osclass_el.get("osfamily", "")
                    os_info["type"] = osclass_el.get("type", "")

        # 3. Extraction détaillée des ports, services, CPE et Scripts NSE
        ports_el = host_el.find("ports")
        if ports_el is not None:
            for port_el in ports_el.findall("port"):
                state_el = port_el.find("state")
                service_el = port_el.find("service")
                
                state = state_el.get("state", "unknown") if state_el is not None else "unknown"
                
                cpes = []
                service_name = ""
                product = ""
                version = ""
                
                if service_el is not None:
                    service_name = service_el.get("name", "")
                    product = service_el.get("product", "")
                    version = service_el.get("version", "")
                    
                    # Récupération de tous les CPEs associés au service
                    for cpe_el in service_el.findall("cpe"):
                        if cpe_el.text:
                            cpes.append(cpe_el.text)
                
                # Récupération des résultats des scripts Nmap (-sC)
                scripts_results = {}
                for script_el in port_el.findall("script"):
                    scripts_results[script_el.get("id", "unknown")] = script_el.get("output", "").strip()

                ports.append({
                    "port": int(port_el.get("portid", 0)),
                    "protocol": port_el.get("protocol", "tcp"),
                    "state": state,
                    "service": service_name,
                    "product": product,
                    "version": version,
                    "cpes": cpes,
                    "scripts_results": scripts_results
                })

        return {"host_status": host_status, "ports": ports, "os_info": os_info}

    async def excutor(self, data: dict) -> dict:
        target = data.get("ip", data.get("domain", data.get("url", "unknown")))

        nmap_path = shutil.which("nmap")
        if nmap_path is None:
            raise ToolNotFoundError("nmap", "nmap tool not found")

        # Port selection. Scanning all 65535 ports with -sV -sC ("-p-") takes
        # 10-30+ minutes per host and makes the tool look frozen, so by default
        # we scan the top ports. Everything is overridable via env vars:
        #   NMAP_PORTS      -> exact spec, e.g. "1-65535" or "80,443,8080"
        #   NMAP_TOP_PORTS  -> N most common ports (default 1000)
        #   NMAP_TIMING     -> timing template (default -T4)
        #   NMAP_TIMEOUT    -> hard timeout in seconds (default 600)
        #   NMAP_EXTRA_ARGS -> extra flags, e.g. "--unprivileged" on cloud hosts
        #                      (e.g. Render) that don't allow raw sockets
        ports_spec = os.getenv("NMAP_PORTS", "").strip()
        if ports_spec:
            port_args = ["-p", ports_spec]
        else:
            port_args = ["--top-ports", os.getenv("NMAP_TOP_PORTS", "1000")]

        timing = os.getenv("NMAP_TIMING", "-T4")

        # -sV (versions), -sC (default scripts), -Pn (skip host-discovery ping —
        # many hosts block ICMP, without this nmap would mark them down and scan
        # nothing), -oX - (XML to stdout).
        extra_args = os.getenv("NMAP_EXTRA_ARGS", "").split()
        cmd = [nmap_path, "-sV", "-sC", "-Pn", timing, *extra_args, *port_args, "-oX", "-", target]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        timeout = float(os.getenv("NMAP_TIMEOUT", "600"))
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            raise ToolInternalError("nmap timed out", tool_name="nmap",
                                    message=f"nmap exceeded {int(timeout)}s")

        print("nmap rc", proc.returncode, "stderr:", stderr.decode()[:200])
        # nmap can exit non-zero yet still emit valid XML; only fail hard if it
        # produced no output at all.
        if proc.returncode != 0 and not stdout.strip():
            raise ToolInternalError(stderr.decode(), tool_name="nmap", message="Tool returned non-zero exit status.")

        parsed = self.parse(stdout)

        # On ne conserve que les ports avec le statut "open" pour l'analyse ultérieure
        open_ports = [p for p in parsed["ports"] if p["state"] == "open"]
        has_web_ports = any(p["port"] in WEB_PORTS for p in open_ports)

        # Structuration du bloc Nmap dans le dictionnaire principal
        data["nmap_result"] = {
            "status": "completed",
            "host_up": parsed["host_status"] == "up",
            "os_info": parsed.get("os_info", {}),
            "open_ports": open_ports,
            "has_web_ports": has_web_ports
        }
        
        return data