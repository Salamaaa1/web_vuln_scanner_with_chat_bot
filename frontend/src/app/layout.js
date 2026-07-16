import './globals.css'

export const metadata = {
  title: 'Security Scanner',
  description: 'Recon & Vulnerability Scanner Framework',
}

export default function RootLayout({ children }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  )
}
