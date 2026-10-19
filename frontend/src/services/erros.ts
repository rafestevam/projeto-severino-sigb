/** Helpers para extrair informações de erros do axios sem depender do formato exato. */

interface RespostaErro {
  response?: { status?: number; data?: { detail?: unknown } }
}

function comoRespostaErro(err: unknown): RespostaErro {
  return err && typeof err === 'object' ? (err as RespostaErro) : {}
}

export function statusHttp(err: unknown): number | null {
  return comoRespostaErro(err).response?.status ?? null
}

export function extrairMensagem(err: unknown, fallback: string): string {
  const detail = comoRespostaErro(err).response?.data?.detail
  return typeof detail === 'string' ? detail : fallback
}
