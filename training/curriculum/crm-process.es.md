# Proceso de CRM y automatización (Zoho)

El CRM es la única fuente de verdad. **Si no está en Zoho, no pasó.** Sin registro, las automatizaciones fallan y otra persona vuelve a llamar al mismo lead.

## 1. Registra cada llamada
- Usa **Log a Call** (o una nota) en el registro **en el momento de la llamada** y luego actualiza el estado.
- Cuando agendas una cita, la nota lleva la lista de handoff completa: nombre y teléfono verificados · dirección · fecha y hora (zona del lead) · quién estará · problema principal · idioma · propietario o arrendatario · notas especiales.
- Crea la tarea de seguimiento en menos de 10 minutos después de la llamada.
- Mantén el **Lead Status** siempre al día. En algunas campañas, pasar el lead a *Contacted* es lo que detiene la secuencia automática: si no actualizas el estado, el lead sigue recibiendo mensajes automáticos.

## 2. Duplicados: por teléfono o email, nunca por nombre
- Busca duplicados por los **últimos 10 dígitos del teléfono** o por **email**.
- **Nunca por nombre.** Mucha gente comparte nombre; en una limpieza real, de 130 grupos con el mismo nombre solo 1 era un duplicado de verdad.
- Las fusiones en Zoho son **irreversibles** y aceptan máximo 3 registros a la vez. Corre el de-duplicate en modo revisión y, si hay cualquier duda, pregúntale a tu manager antes de fusionar.

## 3. Opt-outs el mismo día
- STOP / ALTO / "quíteme" / "no me llame" → marca **Email Opt-Out** y agrega la nota "SMS opt-out" **ese mismo día**.
- En llamada: "Entendido, lo retiro de inmediato." Cuelga y marca no contactar antes de la siguiente marcación. Sin segunda oferta.

## 4. No crees objetos paralelos
**No** crees reglas, plantillas, campos ni vistas nuevas sin que te lo pidan. Si tu manager está editando algo y te manda el link, arregla **ese** objeto. Los duplicados "ciegan" a quien está construyendo el sistema.

## 5. Modelo de campos básico
- Siempre llenos: **Lead Source, Lead Status, Owner**, más el campo maestro de industria que controla las vistas.
- Los campos de cita (quién la agendó, cuándo, para quién) tienen su propia sección: llénalos siempre.
- El idioma es un campo, no una suposición: los leads en español reciben journeys y mensajes en español.

## 6. Plantillas de email: nunca mezclar los sets
| Set | Cuándo se usa |
|---|---|
| **Frío** | Primer contacto con alguien con quien nunca hemos hablado. |
| **Drip tibio** | Tips de nutrición para leads que ya están en un journey. |
| **Post-llamada ("Fue un gusto hablar…")** | **Solo después de una conversación real.** |

Mandarle "fue un gusto hablar" a alguien que nunca habló con nosotros es un error grave.

## 7. Lógica de automatización sobre la que actúas (no la operas)
- Las **secuencias de intentos** avanzan cuando cambia el Lead Status: el estado que pones decide lo que el lead recibe después.
- **Puntaje de engagement:** aperturas, clics y respuestas suman puntos. Puntaje alto = llamas primero y mencionas que notaste su interés, sin decir cómo lo sabes.
- La **asignación de leads calientes** y el **round-robin** envían los leads a quien esté de turno (hora Colombia).
- Tu trabajo **no** es editar esas reglas. Tu trabajo es **actuar rápido cuando llega la notificación** de lead caliente y **reportar** cuando algo no disparó.

### Chequeo diario de automatizaciones
- Un lead nuevo debe mostrar su primer email (Día 0) en la pestaña **Emails** del registro en **5 minutos** o menos.
- Si no aparece: revisa que la regla esté ACTIVA, que el lead tenga email y que los campos de idioma/partner sean correctos. Luego avísale a tu manager **con el nombre del lead** y qué recibió o no recibió.

## 8. La fuente del lead es confidencial
A un cliente o distribuidor solo le entregas: nombre, teléfono, email, dirección/ciudad/ZIP, idioma y notas de la llamada. **Nunca** la descripción del lead ni nombres de formularios o campañas. Si preguntan: "nuestro motor híbrido de leads", y no entres en detalle.

## 9. Verifica antes de reportar
Abre el registro, mira el email enviado, revisa el estado tú mismo/a. Los reportes de herramientas de IA o de otras personas son auto-reportes, no prueba. Lo que no pudiste revisar se reporta como **NO VERIFICADO**.
