---
source: guide/files-and-mail.md
source_hash: 03999c32bb66
---

# Archivos y correo

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/files-and-mail).
:::

Un formulario puede recibir un archivo, una página puede devolver uno, y una
acción puede enviar correo. `projects/helpdesk` usa las tres cosas: tickets con
un adjunto, un correo al equipo de soporte y otro a quien hizo el pedido.

## Recibir un archivo {#taking-a-file}

Declara el archivo como un parámetro de la acción. `accept` y `maxsize` son
reglas como `minlength`: un archivo que no las cumple nunca llega a la acción, y
el formulario muestra el motivo junto al campo.

```xml
<q:action name="open" method="POST">
  <q:param name="title" required="true" minlength="5" />
  <q:param name="attachment" type="file" maxsize="5MB" accept=".png,.jpg,.pdf" />

  <q:if condition="attachment">
    <q:file action="upload" file="{attachment}" result="saved" />
    <!-- saved.filename, saved.original_filename, saved.size, saved.mimetype -->
  </q:if>
  <q:redirect url="/" flash="Ticket opened: {title}" />
</q:action>

<ui:form on-submit="open" submit="Open ticket">
  <ui:input bind="title" />
  <ui:input bind="attachment" />
</ui:form>
```

El formulario sabe que la acción recibe un archivo: envía `multipart/form-data`,
y `attachment` es un campo de archivo que ofrece `.png,.jpg,.pdf`. No escribes
ninguna de las dos cosas.

El archivo se guarda en `paths.uploads` (`./uploads` salvo que la configuración
diga otra cosa), con un nombre seguro; `destination="invoices"` lo pone en una
carpeta dentro de ella. Guarda `saved.filename` — es la forma de volver a
encontrar el archivo.

`q:file action` es `upload`, `delete` o `send` (más abajo); cualquier otra
cosa no pasa el análisis:

```xml
<q:file action="copy" file="{attachment}" />
```

**Error:** `<q:file action="copy">: use upload, delete or send`

Un campo de varias líneas es `<ui:input bind="description" rows="6" />`.

## Devolver un archivo {#handing-a-file-back}

Los archivos subidos **no** se sirven como archivos estáticos: cualquiera con la
URL podría leerlos. Una página envía uno, y decide quién puede tenerlo:

```xml
<!-- components/attachment/[id].q -->
<q:component name="Attachment">
  <q:query name="ticket" datasource="db">
    SELECT attachment, attachment_name FROM tickets WHERE id = :id AND attachment IS NOT NULL
    <q:param name="id" value="{id}" type="integer" />
  </q:query>
  <q:if condition="ticket_result.recordCount == 1">
    <q:file action="send" file="{ticket[0].attachment}" name="{ticket[0].attachment_name}" />
  </q:if>
  <p>There is no attachment for ticket #{id}.</p>
</q:component>
```

`q:file action="send"` termina la página con el archivo como descarga. El nombre
guardado viene de la base de datos, nunca de la URL; una ruta fuera de
`paths.uploads` se rechaza, y un archivo que no existe responde 404. Pon una
guarda en la página (`require_auth`, o un `q:if` con `q:redirect`) y solo lo
recibe quien corresponde.

## Enviar correo {#sending-mail}

Una acción envía un mensaje con `q:mail`; el servidor es la sección `mail:` de
`quantum.config.yaml`. De la receta [Correo en desarrollo](/es/cookbook/files-and-mail/mail-in-development),
probada tal como se muestra:

<<< @/../examples/cookbook/files-and-mail/mail-in-development/components/index.q{xml}

<<< @/../examples/cookbook/files-and-mail/mail-in-development/quantum.config.yaml{yaml}

`host: log` escribe cada mensaje en el log en lugar de enviarlo — úsalo en
desarrollo. Sin una sección `mail:`, `q:mail` es un error que lo dice; nunca
finge que envía:

```xml
<q:mail to="ana@example.com" subject="Welcome">Hello, Ana!</q:mail>
```

**Error:** `q:mail needs a mail server`

### Cuando el servidor dice que no {#when-the-server-says-no}

Un mensaje que el servidor no acepta detiene la acción con el motivo del
servidor. Cuando el resto de la acción debe ocurrir igual, pon
`onerror="continue"` y verifica `<name>_result.success` — de la receta
[Cuando el servidor de correo dice que no](/es/cookbook/files-and-mail/mail-server-refuses),
donde el pedido se guarda aunque no se pueda enviar su confirmación:

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/components/index.q{xml}

El helpdesk (`projects/helpdesk`) hace lo mismo: guarda primero el ticket y
dice, en su mensaje, cuándo no se pudo enviar un correo.

## Reglas {#rules}

[FILE-1, FILE-2, MAIL-1, MAIL-2 y UI-14](https://github.com/danielgregorio/quantum/blob/main/SPEC.md)
en la SPEC.
