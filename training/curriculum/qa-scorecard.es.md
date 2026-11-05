# Scorecard de QA y checklists antes de enviar

Cada campaña activa (outbound de GSD, campañas de clientes y cualquier otra campaña de GSD) tiene QA. Calificas llamadas, revisas datos y frenas cualquier envío que no esté listo.

## 1. Qué revisas y cada cuánto

| Tipo de QA | Qué revisas | Frecuencia |
|---|---|---|
| **Llamadas** | Muestra de llamadas grabadas, calificadas con el scorecard de abajo | Diario (mín. 5 llamadas) |
| **Datos del CRM** | Campos obligatorios, Lead Status correcto, notas, duplicados, idioma, opt-outs marcados | Diario (registros del día) + semanal (vista completa) |
| **Email antes de enviar** | Ortografía, idioma, merge tags, remitente, diseño del cliente, sin placeholders, sin links no aprobados, sin mención de la fuente del lead | Antes de **cada** envío o plantilla nueva |
| **SMS antes de enviar** | Línea correcta, historial completo de STOP, supresión de 14 días, marca correcta, segundo "go" | Antes de **cada** envío masivo |
| **Automatizaciones** | Workflows disparados, webhooks OK, sin envíos duplicados | Diario |

## 2. Scorecard de llamadas (100 puntos)

| # | Criterio | Puntos | Qué se espera |
|---|---|---|---|
| 1 | Apertura | 10 | Saludo, nombre, empresa/marca correcta, motivo de la llamada en menos de 15 s. Sonrisa en la voz. |
| 2 | Permiso y rapport | 10 | Usa el nombre del prospecto (3 veces), pregunta si es buen momento, adapta su ritmo. |
| 3 | Descubrimiento | 20 | Preguntas abiertas: problema, situación, quién decide, urgencia. Pausa y escucha. |
| 4 | Manejo de objeciones | 15 | Acuerda → empatiza → redirige. Nunca discute. Usa las respuestas del playbook. |
| 5 | Cierre de la cita | 20 | Ofrece dos opciones de horario, confirma fecha, hora (zona del lead), dirección y quién estará. |
| 6 | Cumplimiento y marca | 15 | No revela la fuente del lead, no da precios no autorizados, respeta el "no", idioma correcto, sin promesas falsas. |
| 7 | Registro en CRM | 10 | Nota completa con la lista de handoff, estado actualizado, tarea de seguimiento creada en ≤ 10 min. |
| | **Total** | **100** | |

### Rangos
- **Good (85–100):** la llamada agenda o avanza. Guárdala como ejemplo de entrenamiento.
- **Bad (60–84):** errores corregibles. Anota 1–2 cosas puntuales a mejorar.
- **Ugly (< 60 o cualquier falla crítica):** riesgo de cumplimiento, de marca o de cliente. **Se escala a tu manager el mismo día.**

### Fallas críticas (Ugly automático)
- Revelar de dónde vienen los leads.
- Dar un precio sin autorización.
- Ignorar un "no me llame" o un STOP.
- Mentir u ofrecer algo que no existe.
- Faltarle el respeto al prospecto.
- Agendar sin confirmar dirección y hora.

## 3. Checklist antes de enviar — email (60 segundos)
- [ ] Marca y diseño del cliente correctos
- [ ] Idioma correcto (los leads en español reciben español)
- [ ] Nombre y dirección del remitente correctos
- [ ] Merge tags probados con un registro real; ningún `${...}` vacío
- [ ] Sin placeholders (por ejemplo, una dirección postal falsa en el pie)
- [ ] Sin links ni dominios nuevos no aprobados
- [ ] Sin mención de la fuente del lead
- [ ] Copia de revisión enviada a tu manager → "ok" explícito de tu manager registrado

## 4. Checklist antes de enviar — SMS
- [ ] Sale de la línea de texto registrada **10DLC de la empresa**; la otra línea es solo para llamadas
- [ ] Historial completo revisado para cada número: fuera quien haya dicho STOP / ALTO / baja **alguna vez**
- [ ] Fuera quien recibió texto de la línea de texto registrada en los **últimos 14 días**
- [ ] Fuera los opt-outs del CRM
- [ ] Marca confirmada (debe ser la que tu manager nombró; si hay duda, pregunta)
- [ ] Horario de envío 8 a.m. – 8 p.m. en la zona del lead
- [ ] Lista final mostrada a tu manager → **segundo "go" explícito** registrado

Elegir un plan ("vamos con la A") **no** es aprobar un envío. Cada envío necesita su propio OK.

## 5. Cuándo escalar a tu manager (y cuándo no)
**Sí escalas:** decisiones de dinero, contratos, cualquier envío o publicación, cambios en vivo, llamadas Ugly, incidentes con un lead real, accesos o licencias nuevas.

**No escalas:** problemas técnicos que puedes resolver, mover tarjetas, limpiar datos sin borrar nada, preguntas que esta academia ya responde.

**Cómo:** primero intenta resolverlo y después escala **en un solo mensaje claro**: qué pasó, qué ya intentaste y qué decisión necesitas.

**Si te equivocaste:** dilo primero, en simple, y después explica qué está corriendo ahora. Esconder un error es peor que el error.
