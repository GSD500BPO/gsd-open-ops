# SCRUM y el tablero de Trello

Eres la **Scrum Master humana** (o el Scrum Master humano) del tablero del equipo. Tu trabajo: mantener las tarjetas en movimiento, desbloquear al equipo (personas y agentes de IA) y proteger el tiempo de tu manager. **tu manager se dedica a cerrar negocios.** Solo escalas lo que únicamente él puede decidir.

> Estrella del norte: **"¿Esto nos está haciendo ganar dinero?"** La prioridad se ordena por impacto en ingresos.

## Accesos (los hace tu manager, no tú)
Tu manager te invita a Trello como miembro normal, crea tu usuario de Zoho (una licencia paga: decisión suya), te da acceso al sistema telefónico y un email de trabajo. Día 1: acepta las invitaciones → activa 2FA en Trello y Zoho → guarda todo en el gestor de contraseñas. **Nunca pegues tokens ni contraseñas en tarjetas, comentarios o chats.**

## El flujo

```
Backlog → Sprint (semana actual) → Haciendo → Revisión → We Get Sh*t Done!
                          ↘ Bloqueado (con motivo escrito) ↗
```

- **Backlog:** todo trabajo nuevo y sin agendar entra aquí.
- **Haciendo:** máximo **2 tarjetas por persona o agente**.
- **Revisión:** espera la aprobación de tu manager antes de pasar a producción.
- **Bloqueado:** siempre con el motivo escrito en la tarjeta.
- Si el tablero todavía no tiene lista de sprint, propónsela a tu manager; mientras tanto, marca las tarjetas del sprint con la etiqueta "Planning".
- Nunca borres etiquetas ni listas por tu cuenta: propón la limpieza a tu manager.

## Plantilla de tarjeta

Título: `[Marca] Verbo + resultado concreto`. Ejemplo: `[GSD] Confirmar las 3 citas de la semana`.

```
## Objetivo (1 línea, en términos de dinero/cliente)
## Definition of Done (checklist)
- [ ] ...
- [ ] Evidencia adjunta (link, captura, ID del registro en Zoho)
- [ ] Revisado por: ____
## Siguiente acción  <qué, quién, cuándo>
## Bloqueos          <ninguno | descripción + a quién se escaló + fecha>
## Notas             <fecha — actualización corta>
```

**Obligatorio en cada tarjeta:** dueño (etiqueta + miembro asignado), estrellas honestas, valor ($, $$, $$$), fecha límite, marca.

### Escala de estrellas (no infles)
| Estrellas | Significa | Ejemplo |
|---|---|---|
| 1 | Trivial: cambio de texto o configuración | Corregir un typo en una plantilla |
| 2 | Pequeño: un solo cambio o arreglo | Editar el texto de un PDF de bienvenida |
| 3 | Mediano: varias piezas, alguna integración | Nueva vista de Zoho + reporte semanal |
| 4 | Grande: sistema nuevo, varios componentes | Rehacer un formulario de captura completo |
| 5 | Mayor: infraestructura base, alto impacto en ingresos | Lanzar un territorio nuevo |

Antes de poner 5 estrellas pregúntate: **"¿De verdad es trabajo de 5 estrellas?"**

## Ceremonias

| Ceremonia | Cuándo | Duración | Qué produce |
|---|---|---|---|
| **Daily standup** | L–V 8:00 a.m. COT | 15 min máx. | Resumen escrito |
| **Sprint planning** | Lunes 8:15–8:45 | 30 min | 5–12 tarjetas comprometidas, ordenadas por $$$ |
| **Grooming del backlog** | Miércoles 5:15–5:45 | 30 min | Cada tarjeta con dueño, estrellas y siguiente acción |
| **Sprint review** | Viernes 4:30–5:00 | 30 min | Qué se terminó (con evidencia) y qué espera en Revisión |
| **Retro** | Viernes 5:00–5:15 | 15 min | 1 cosa que seguimos, 1 que dejamos, 1 que empezamos |

### Plantilla de standup
```
STANDUP <fecha>
Ayer: <tarjetas movidas a Done/Revisión>
Hoy: <máx. 2 por persona/agente en Haciendo>
Bloqueos: <tarjeta → motivo → quién lo destraba → desde cuándo>
Citas: semana __/4 mín.
Solo tu manager: <decisiones que SOLO tu manager puede tomar, o "ninguna">
```

## Reglas de juego
- **Máximo 2 tarjetas por persona o agente en Haciendo.**
- **Regla de 2 horas:** si una tarjeta en Haciendo no avanza en 2 h, interviene: pregunta, divídela o pásala a Bloqueado con el motivo.
- **Anti-loop:** no repitas la misma información ni reintentes un enfoque que ya falló. Cambia de enfoque o escala.
- **Revisión es obligatoria** antes de producción. Tu manager aprueba.
- **Todo lo externo es Solo tu manager:** envíos, publicaciones, anuncios, pagos, contratos, créditos de telefonía y creación de cuentas.
- Cuando una tarjeta termina pasa a Revisión → tú jalas la siguiente del sprint.
- **Agentes de IA:** se les habla solo por el dashboard de agentes del equipo, nunca por otros canales.

## Definition of Done
Una tarjeta pasa a **We Get Sh\*t Done!** solo si:
1. Toda la checklist está marcada.
2. Hay **evidencia** adjunta (link, captura, ID de Zoho, log). "Ya está" no es evidencia.
3. Alguien distinto del autor lo **verificó en vivo**. Los auto-reportes de IA no cuentan por sí solos.
4. Si toca algo externo, la **aprobación explícita de tu manager** quedó registrada en la tarjeta (fecha + texto del OK).
5. El CRM quedó actualizado (estado, nota) si la tarea toca leads o clientes.
6. Las estrellas y el valor se revisaron al cerrar.
7. Lo pendiente quedó como tarjeta nueva en Backlog, enlazada.

## Tus primeras 2 semanas
| Día | Tarea |
|---|---|
| Día 1 | Aceptar invitaciones. Leer este módulo y los de CRM y QA. Observar el tablero sin mover nada. |
| Día 2 | Primer standup. Inventario de la lista Bloqueado: tarjeta, dueño, motivo, antigüedad. |
| Día 3 | Proponer a tu manager **en un solo mensaje**: qué archivar, qué reactivar y qué necesita decisión suya. |
| Día 4 | Aplicar lo aprobado. Revisar que cada tarjeta del Backlog tenga dueño, estrellas y $. |
| Día 5 | Primera sprint review + retro. Proponer la lista de sprint y la limpieza de etiquetas duplicadas. |
| Semana 2 | Repetir el ciclo completo. Extender el grooming a los tableros de clientes (uno por día). |
