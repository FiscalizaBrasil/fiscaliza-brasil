const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"

export function absolutizeFoto(foto: string | undefined, fallbackUrl?: string): string {
  if (!foto) return fallbackUrl || "/placeholder-user.svg"
  if (foto.startsWith("/")) return `${API_URL}${foto}`
  return foto
}
