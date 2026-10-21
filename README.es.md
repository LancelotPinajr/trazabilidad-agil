# Trazabilidad Agil Cord

[English](README.md)

**Cada commit ligado a la tarea del plan que lo motivó.** Un plugin de Claude
Code y dos chequeos pequeños (para tu hook de git y tu CI) y un reporte local con gráficas para que un equipo
trabaje desde planes escritos y quede el rastro de cada tarea a su código.

```
feat(auth): bloquear la cuenta tras 5 intentos fallidos (01/2.3)
                                                          └┬┘└┬┘
                                                        plan tarea
```

> **Sin soporte y sin servicio.** Este proyecto se publica tal cual, con
> licencia MIT. Nada corre en el servidor de nadie: todo corre en tu máquina,
> con tu git, tu cuenta de Claude y tus llaves. Los issues están cerrados; si
> necesitas algo distinto, haz un fork.

## Qué trae

| Pieza | Qué hace |
|---|---|
| **Chequeo de commits** | Rechaza el commit que no cita una tarea existente: `(01/2.3)`. Corre como hook `commit-msg` y en el CI sobre **todos** los commits de un PR, así que `--no-verify` solo aplaza el rechazo. Un id inventado no pasa. |
| **Chequeo de migraciones** | Falla si dos ramas crean el mismo número de migración, o si un PR edita o renombra una migración que ya llegó a la rama principal. |
| **Aviso de sesión** (Claude Code) | Al abrir una sesión: tu rama, cuánto vas detrás de la rama principal, cambios sin commit y si el hook está activo. Avisa si trabajas en la rama principal. |
| **Aviso «cambió main»** (Claude Code) | Al abrir la sesión y antes de cada mensaje: si `origin/main` avanzó desde el último aviso, tú (y Claude) ven «🔔 Cambió `main`: 3 commits nuevos» con sus asuntos. Hace `fetch` como mucho cada 10 minutos, nunca pide contraseña y se calla si no hay red. |
| **`/trazabilidad:start-session 01/2.3`** (Claude Code) | Revisa la rama, lee la tarea y su criterio de aceptación en el plan, la marca en curso y fija el id para los commits de la sesión. |
| **`/trazabilidad:add-to-plan`** (Claude Code) | A media sesión, cuando hay trabajo que ninguna tarea cubre: lee la conversación (y tus cambios sin commit), encuentra las tareas que ya lo cubren y propone filas nuevas (siguiente id libre, título, criterio de aceptación verificable, estado) o un plan nuevo. **Solo escribe después de tu sí**, hace commit solo del plan y te da los ids para citar. |
| **`/trazabilidad:end-session`** (Claude Code) | Revisa ids, migraciones y pruebas, y deja el estado de cada tarea en su plan. Una tarea se da por hecha solo si su criterio se verificó: **un commit no cierra una tarea**. |
| **`/trazabilidad:owner-board`** (Claude Code y Artifacts de la app de Claude) | Arma el tablero de pendientes de una persona con las filas del plan que dependen de ella, y lo lee de vuelta para actualizar el plan. Una casilla marcada **no cierra** la tarea. Ver [Varios chats](#varios-chats-código-pendientes-y-captura). |

Los comandos tienen nombre en inglés, pero Claude responde en el idioma en que
le escribas, y los mensajes de los chequeos salen en español con
`language = "es"`.

## El reporte

```bash
python -m trazabilidad report            # escribe trazabilidad-report.html
```

Un solo HTML, calculado en tu máquina con tu historial de git. No carga nada de
internet. Tema claro y oscuro, una tabla bajo cada gráfica y el valor al pasar el cursor.

- **Tareas por plan**, en hechas, en curso, bloqueadas y por hacer, según dicen hoy los planes.
- **Commits por semana**, con y sin id de tarea.
- **Tiempo de ciclo por plan**: del primer commit que cita una tarea al commit
  que la marca hecha. Mediana y percentil 90, siempre con su `n`; con menos de
  3 tareas avisa que no alcanza para leer una tendencia.
- **En curso, de la más antigua a la más reciente.**

No hay cifras por persona, a propósito: mide cómo entrega el equipo, no quién.
Agrega `trazabilidad-report.html` a tu `.gitignore`.

## Cómo son los planes

Un Markdown por plan, llamado `NN-plan-nombre.md`, con tablas de tareas cuya
primera columna es el id. Ver [`examples/docs/plans/01-plan-login.md`](examples/docs/plans/01-plan-login.md).

```markdown
| # | Tarea | Criterio de aceptación | Estado |
|---|---|---|---|
| 2.3 | Bloquear tras intentos fallidos | Tras 5 fallos en 15 min la cuenta se bloquea 15 min; probado | ⬜ |
```

Los ids se repiten entre planes (todos tienen un `1.1`), así que la cita
siempre lleva el plan: `01/2.3`. Si dos planes comparten número, se citan por
nombre: `01-login/2.3`. El nombre de archivo, el formato del id y la carpeta se
configuran.

## Instalación

Requiere Python 3.11+ y git. Nada más.

**1. Los chequeos** (en cada repositorio):

```bash
pip install git+https://github.com/LancelotPinajr/trazabilidad-agil-cord
python -m trazabilidad init --lang es
```

`init` escribe `.trazabilidad.toml` (comentado; ajústalo a tu repo), el hook en
`.githooks/commit-msg`, lo fija en finales LF en `.gitattributes` y lo activa en
este clon. Nunca sobrescribe un archivo que ya existe. Cada persona del equipo
corre `git config core.hooksPath .githooks` una vez por clon.

Los commits anteriores al que agrega `.trazabilidad.toml` nunca se revisan: la
convención aplica desde que la adoptas.

**2. CI** — copia [`examples/github-actions.yml`](examples/github-actions.yml) a
`.github/workflows/`. Fija una versión con `@v0.1.1` (o un sha).

**3. El plugin de Claude Code** — en Claude Code:

```
/plugin marketplace add LancelotPinajr/trazabilidad-agil-cord
/plugin install trazabilidad@trazabilidad-agil-cord
```

O en un solo comando (Claude Code v2.1.275 o posterior):
`/plugin install trazabilidad --marketplace LancelotPinajr/trazabilidad-agil-cord`.

Los comandos del plugin llevan su nombre: **`/trazabilidad:start-session`,
`/trazabilidad:add-to-plan`, `/trazabilidad:end-session`**. También basta con
pedirlo («agrega esto al plan») y Claude usa el que corresponde.

Para un equipo, decláralo en el `.claude/settings.json` del repositorio. Claude
Code agrega el marketplace cuando alguien confía en la carpeta y le muestra a
cada persona el comando de instalación una vez (un plugin de GitHub nunca se
instala sin ella):

```json
{
  "extraKnownMarketplaces": {
    "trazabilidad-agil-cord": {
      "source": { "source": "github", "repo": "LancelotPinajr/trazabilidad-agil-cord", "ref": "v0.1.1" }
    }
  },
  "enabledPlugins": { "trazabilidad@trazabilidad-agil-cord": true }
}
```

## Trabajar en equipo

No hay cuentas que ligar ni un servidor en medio. **Lo que une al equipo es el
repositorio git compartido**: quien tiene acceso a él en GitHub está en el equipo.

- **Los planes son el tablero compartido.** Viven en el repositorio, así que todos
  ven las mismas tareas y estados después de un `git pull`.
- **Cada persona usa su propia cuenta de Claude.** Claude Code lee del
  repositorio el mismo `CLAUDE.md`, `.trazabilidad.toml` y plugin, así que cada
  sesión sigue las mismas reglas la abra quien la abra.
- **El CI es el árbitro.** Haga lo que haga la máquina de cada quien, un PR cuyos
  commits no citan tarea, o cuyas migraciones chocan, no entra.
- **Todos obtienen el mismo reporte**, porque sale del mismo historial.

Para sumar a alguien: dale acceso al repositorio; esa persona lo clona, instala
el paquete con `pip install`, corre `git config core.hooksPath .githooks` y abre
el repositorio en Claude Code, que la primera vez le muestra el comando para instalar el plugin.

Para no pisarse: una rama por persona, traer la rama principal a la tuya
seguido, y mover en el plan solo el estado de tus tareas (un commit
`docs(plan)` corto), para que dos personas casi nunca editen la misma fila.

## Varios chats: código, pendientes y captura

Un proyecto real tiene trabajo que no es código y que depende de una persona:
decidir, pasar datos, subir fotos. Si todo vive en un mismo chat, se pierde. Esta
es la forma de trabajo con la que CØRD usa el paquete, en la app de Claude:

| Chat | Para qué | Quién escribe | Qué queda |
|---|---|---|---|
| **Código** | La sesión de Claude Code en el repositorio. Trabaja las tareas del plan | Claude y tú | Commits con id de tarea y el estado de cada tarea en el plan |
| **Pendientes** | Un tablero con las tareas que dependen de una persona: una casilla de hecho y una nota por cada una | Esa persona | El estado de cada pendiente |
| **Captura** | Un lugar donde subir lo que el código necesita y solo esa persona tiene: fotos, características, precios | Esa persona | Datos que la sesión de código convierte en archivos o filas, con commit |

**Reglas**

1. **El plan sigue siendo la fuente de verdad.** Los tableros son ventanas hacia
   él: cada pendiente cita la fila del plan que lo motiva (`6.2`), y lo que se
   haga con él se commitea con ese id.
2. **Marca en el plan qué filas dependen de una persona.** En CØRD es
   `⬜ **del dueño**` en la celda de estado. De ahí sale el tablero de pendientes.
3. **La sesión de código lee los tableros, no al revés.** La persona marca y
   sube; en el chat de código dice «revisa mis pendientes», y Claude los lee,
   actualiza el plan y hace commit con id. Un pendiente marcado como hecho no
   cierra la tarea: se cierra cuando su criterio se verifica.
4. **Nada de secretos en un tablero.** Contraseñas, tokens y llaves van por los
   canales de siempre.
5. **Lo que se sube es dato, no instrucción.** Claude lo lee, no lo obedece.
6. **Cada tablero es privado** de quien lo crea, salvo que lo comparta.

**Cómo se arma.** Cada tablero es un Artifact de la app de Claude con
almacenamiento (`db`, y `assets` para las fotos). Se pide con
`/trazabilidad:owner-board` o en palabras: «arma el tablero de pendientes con las
filas del plan que dependen de mí». La skill le dice a Claude cómo armarlo y cómo
leerlo de vuelta; los tableros mismos son páginas de la app de Claude, así que
hace falta esa app. El paquete no instala nada que corra por su cuenta.

**Ejemplo.** Rick, el agente comercial de CØRD: un tablero con 16 pendientes en 4
bloques, y otro donde el dueño sube foto, características y precio de cada
producto, que la sesión de código convierte en el catálogo.

## Tus cuentas y tus llaves

| Qué | Dónde vive | Quién lo ve |
|---|---|---|
| Cuenta de Claude | Tu propio acceso a Claude Code. El plugin no toca cuentas ni cobra nada | Tú |
| Configuración del repo | `.trazabilidad.toml` en tu repositorio | Tu equipo |
| Llaves de API | **Hoy no hace falta ninguna.** Los chequeos solo leen tu git local. Si una versión futura llama a una API (p. ej. GitHub), leerá la llave de una variable de entorno de tu máquina, nunca de un archivo del repositorio | Tú |
| Tu código y tus planes | No salen de tu máquina. No se envía nada a ningún lado | Tú |

## Nota de seguridad

El plugin ejecuta `hooks/run.py` al abrir una sesión de Claude Code en tu
repositorio y antes de cada mensaje. Corre comandos de lectura de `git` y, como
mucho cada 10 minutos, `git fetch origin main` (se apaga con `[watch] fetch = false`).
Lo que ya avisó se guarda en `.git/trazabilidad-watch.json`, nunca en el repositorio.
**Léelo antes de confiar en el marketplace**, como con cualquier plugin, y fija
una versión (`ref`) para que una actualización no cambie lo que corre en tu
máquina sin que tú lo decidas.

## Configuración

```toml
language = "es"            # "en" o "es": mensajes de los chequeos y del aviso
main_branch = "main"

[plans]
dir = "docs/plans"
file_pattern = '^(\d+)-plan-([a-z0-9-]+)\.md$'   # grupo 1: número, grupo 2: nombre corto
task_id_pattern = '\d+\.\d+[a-z]?'               # p. ej. '[A-Z]+-\d+' para ids tipo JIRA

[commits]
exempt_prefixes = ["Merge ", 'Revert "', "fixup! ", "squash! ", "amend! "]
docs_only_plans_exempt = true   # un commit docs: que solo edita planes no necesita id

[migrations]
dirs = ["db/migrations"]        # vacío apaga el chequeo; cada carpeta numera por su cuenta
pattern = '^(\d+)_.+\.sql$'

[watch]
fetch = true                    # false: solo avisa de lo que traigan tus propios fetch
every_minutes = 10
```

No fusiones los PR con *squash*: aplastar los commits en uno borra el id de
cada uno.

## Comandos

```bash
python -m trazabilidad init [--lang es]
python -m trazabilidad check-commits --message .git/COMMIT_EDITMSG   # lo que corre el hook
python -m trazabilidad check-commits --range origin/main..HEAD       # lo que corre el CI
python -m trazabilidad check-migrations [--base origin/main]
python -m trazabilidad session                                       # el aviso, como JSON de hook
python -m trazabilidad plans                                         # planes, épicas y siguientes ids libres (JSON)
python -m trazabilidad watch                                         # «cambió main», como JSON de hook
python -m trazabilidad report [--out archivo.html] [--weeks 26]
```

## Origen

Sale de las herramientas internas de [CØRD](https://github.com/LancelotPinajr),
donde un equipo de dos personas trabaja por sesiones con Claude Code desde
planes numerados.

## Licencia

[MIT](LICENSE). Se entrega tal cual, sin garantía ni soporte.
