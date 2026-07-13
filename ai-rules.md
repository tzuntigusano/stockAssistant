# Reglas de interacción para IAs (Claude, Cursor, etc.)

1. **Lee `CLAUDE.md` primero.** Contiene arquitectura, endpoints, BD, reglas críticas y estado. NO re-explores el árbol completo ni releas archivos para "orientarte".
2. **Castellano siempre** en respuestas y en textos de UI.
3. **Diffs mínimos:** edita con parches quirúrgicos (Edit/str_replace). Nunca reescribas un archivo entero si cambias <30% de él.
4. **Lecturas parciales:** lee solo el rango de líneas que necesitas de archivos >150 líneas.
5. **Conciso y directo:** sin preámbulos, sin repetir lo que el usuario ya sabe, sin opciones que no vas a recomendar.
6. **No inventes alcance:** ni features, ni refactors, ni renombrados no pedidos.
7. **Conserva los comentarios de "porqué"** (decisiones no obvias: MultiIndex, pandas-ta, límites de APIs). Solo elimina comentarios que repiten el código.
8. **Verifica antes de afirmar:** backend → `pytest` y `ruff check .` (rápido, sin reiniciar) para lógica de `core/`; para endpoints, reiniciar uvicorn + `Invoke-RestMethod`. Frontend → `npm run typecheck` + preview/HMR + consola. Si un test falla, dilo con la salida.
9. **Secretos:** viven en `backend/.env` (gitignored). No los muestres en logs ni respuestas.
10. **El LLM de la app solo redacta** — cualquier lógica de decisión nueva va en código determinista (core/), jamás en prompts.
