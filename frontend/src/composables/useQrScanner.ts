import { ref, type Ref } from 'vue'

/**
 * useQrScanner — composable que converte um campo de input em receptor de
 * leitores QR/barcode USB (que agem como teclado com Enter no final).
 *
 * Uso:
 *   const inputRef = ref<HTMLInputElement | null>(null)
 *   const { attach, detach } = useQrScanner(inputRef, (codigo) => { ... })
 *
 * @param inputRef  Ref para o elemento <input> que receberá o foco.
 * @param onScan    Callback chamada com o valor lido quando Enter é pressionado.
 */
export function useQrScanner(
  inputRef: Ref<HTMLInputElement | null>,
  onScan: (value: string) => void,
) {
  const isAttached = ref(false)

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      const el = inputRef.value
      if (el && el.value.trim()) {
        onScan(el.value.trim())
        el.value = ''
      }
    }
  }

  function attach() {
    const el = inputRef.value
    if (el && !isAttached.value) {
      el.addEventListener('keydown', handleKeydown)
      el.focus()
      isAttached.value = true
    }
  }

  function detach() {
    const el = inputRef.value
    if (el && isAttached.value) {
      el.removeEventListener('keydown', handleKeydown)
      isAttached.value = false
    }
  }

  return { attach, detach, isAttached }
}
