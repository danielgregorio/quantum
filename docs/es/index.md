---
layout: home
title: Quantum
hero:
  name: Quantum
  text: Aplicaciones web a partir de páginas declarativas
  tagline: Base de datos, formularios, sesiones e IA en el lenguaje. Sin cadena de build, sin JavaScript, sin framework de front-end.
  actions:
    - theme: brand
      text: Empezar
      link: /es/guide/quick-start
    - theme: alt
      text: Por qué Quantum
      link: /es/guide/why-quantum
    - theme: alt
      text: Ver en GitHub
      link: https://github.com/danielgregorio/quantum

features:
  - icon: "🎯"
    title: Una página, de arriba abajo
    details: Guardas, acciones, consultas y la pantalla en el orden en que se ejecutan. Sin JavaScript que escribir.
  - icon: "🖥️"
    title: Navegador, terminal, escritorio
    details: La misma página funciona en un navegador (quantum start), en una terminal (quantum console) y en una ventana de escritorio (quantum desktop).
  - icon: "🧾"
    title: Formularios que conocen sus reglas
    details: Un formulario toma de los q:param de su acción lo obligatorio, las longitudes, los tipos y las opciones, y se verifica en el navegador y en el servidor.
  - icon: "🗃️"
    title: SQL en el que puedes confiar
    details: Consultas parametrizadas, un plan de esquema declarativo, historial de cambios y quantum check contra tu base de datos.
  - icon: "🤖"
    title: IA en el lenguaje
    details: q:llm responde a partir de tus documentos, con fuentes y en streaming; q:agent llama herramientas que escribes en Quantum.
  - icon: "✅"
    title: Especificado y probado
    details: Cada regla de la especificación tiene una prueba; las aplicaciones de ejemplo se ejecutan de punta a punta en CI.
source: index.md
source_hash: 15bee710f3f5
---

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/). Por ahora, la mayor parte de la
documentación está en inglés.
:::

# Bienvenido a Quantum

Quantum construye **aplicaciones web a partir de páginas XML declarativas**; la
misma página también funciona en una terminal y en una ventana de escritorio.
Inspirado en ColdFusion y Adobe Flex, te permite construir herramientas
internas, paneles y aplicaciones de IA sin escribir JavaScript.
[¿Por qué Quantum?](/es/guide/why-quantum)

## Ejemplo rápido

Una página que lista notas desde una base de datos y agrega una desde un
formulario, con la regla del campo, la inserción y el mensaje posterior
incluidos:

<<< @/../examples/cookbook/testing/first-test/components/index.q{xml}

Esta página y su prueba se ejecutan en cada cambio; ver la receta
[A first test with quantum test](/cookbook/testing/first-test) (en inglés).

## Funcionalidades principales

### El lenguaje
- **Componentes**: archivos `.q` reutilizables con parámetros y valores de retorno
- **Manejo de estado**: `q:set` para variables con validación y verificación de tipos
- **Bucles**: iteraciones sobre rangos, arrays, listas y consultas con `q:loop`
- **Condicionales**: `q:if`/`q:elseif`/`q:else` completos
- **Funciones**: lógica reutilizable con `q:function`

### Pantallas (`ui:*`)
- **Un conjunto del Núcleo**: ventanas, cajas, paneles, tablas, listas, formularios y campos ([UI](/guide/ui))
- **Tres renderizadores**: navegador, terminal y ventana de escritorio, a partir de la misma página
- **Formularios desde las acciones**: los campos, las reglas y los errores vienen de los `q:param` de la acción
- **Tablas desde las consultas**: paginación, búsqueda mientras escribes, celdas ordenables y editables

### Backend
- **Consultas a bases de datos**: SQL con parámetros, planes de esquema, historial de cambios, `quantum check`
- **Autenticación**: manejo de sesiones y control de acceso por roles
- **Importación de datos**: fuentes JSON, CSV y XML
- **Archivos y correo**: archivos subidos, descargas protegidas y `q:mail` ([guía](/guide/files-and-mail))
- **IA**: `q:llm` con fuentes y streaming, `q:knowledge`, `q:agent` ([guía](/guide/ai))

## Filosofía

> **Simplicidad por encima de la configuración**

Quantum prioriza la legibilidad y la facilidad de uso. Si sabes XML y SQL,
puedes construir aplicaciones completas.

## Primeros pasos

```bash
pip install quantum-framework
quantum start          # in an application folder; the guide builds one step by step
```

[Lee la guía de inicio rápido](/es/guide/quick-start)
