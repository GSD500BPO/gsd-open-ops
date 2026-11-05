# GSD Open Ops: kit de código abierto para agendamiento de citas y operaciones BPO

**Gratis y con licencia MIT: un bot de reclutamiento por WhatsApp con calificación automática de candidatos, una academia de 23 módulos para setters (inglés y español), plantillas de cadencias de venta, reglas de CRM y un recorrido (journey) de 96 pasos para todo el año, pensado para negocios de servicios para el hogar.**

> **Regalamos la salsa.** Esto es lo que usamos todos los días en [GSD 500 BPO](https://gsd500bpo.com/?utm_source=github&utm_medium=readme_es&utm_campaign=open-ops): cómo reclutamos, evaluamos, entrenamos y dirigimos setters bilingües para dealers de tratamiento de agua y empresas de servicios para el hogar. Lo construyó un solo fundador, con Claude como socio de ingeniería.
>
> **¿Quieres que lo operemos por ti? → [Agenda una llamada de estrategia](https://gsd500bpo.com/strategy-call?utm_source=github&utm_medium=readme_es&utm_campaign=open-ops)**

*English: [README.md](README.md)*

## Qué hay adentro

| Carpeta | Qué es |
|---|---|
| [`recruiting/`](recruiting/) | **Ramón**, el bot de reclutamiento por WhatsApp: registro → pasos por WhatsApp → video de 1 minuto en inglés → puntaje de speaking local (claridad, fluidez, gramática, acento) → prueba de inglés, ventas y mecanografía → roleplay de voz → filtro aprobado/no aprobado → tarea de entrevista |
| [`training/`](training/) | La **academia de setters**: 23 módulos en EN y ES (archivos `*.es.md`), quizzes, graduación 3-3-3, plantillas de SOP y el mapa de roles |
| [`crm/`](crm/) | Reglas del equipo: speed to lead (15 min), una tarea abierta siempre, regla de 3 días vencidos, intentos TA-1..4, seguimientos FU-1..6 |
| [`playbooks/`](playbooks/) | El **recorrido de 96 pasos para todo el año**: qué hacer con cada lead que no compró (PDF + CSV + JSON) |
| [`USE-CASES.md`](USE-CASES.md) | 8 casos de uso paso a paso |

## Para quién es

- Call centers y BPOs que contratan SDRs / setters bilingües.
- Dealers de tratamiento de agua y empresas de HVAC, solar, techos, ventanas y restauración.
- Emprendedores solos que quieren ver cómo se opera reclutamiento, entrenamiento y CRM con IA.

## Inicio rápido

```bash
git clone https://github.com/GSD500BPO/gsd-open-ops.git
cd gsd-open-ops/recruiting/ramon
cp .env.example .env && chmod 600 .env
python3 tests/test_offline.py     # prueba en seco, sin red: "OK 10 checks"
```

1. **Contrata con Ramón** (en seco un día, luego solo tu teléfono, luego todos).
2. **Entrena con la academia** (`training/curriculum/*.es.md`).
3. **Dirige el piso con las reglas de CRM** (`crm/`).
4. **No desperdicies ningún lead**: primero las reglas de salida (STOP es permanente), luego los 96 pasos.

## Preguntas frecuentes

**¿Es gratis para uso comercial?** Sí, licencia MIT.
**¿Necesito Zoho?** No. Las reglas funcionan en cualquier CRM con tareas, etapas, notas y etiquetas; el recorrido incluye mapa para Zoho, GoHighLevel y HubSpot.
**¿Cómo califica el bot?** Prueba (compuesto ≥ 65, inglés ≥ 70) + video + speaking ≥ 60/100, calculado en tu propio servidor. Una persona siempre toma la decisión final.
**¿El bot hace spam?** No: en seco por defecto, límites diarios por candidato, STOP permanente y nada público sin un SÍ del candidato.

**¿Quieres que lo operemos por ti? → [Agenda una llamada](https://gsd500bpo.com/strategy-call?utm_source=github&utm_medium=readme_es&utm_campaign=open-ops)**

Licencia: [MIT](LICENSE)
