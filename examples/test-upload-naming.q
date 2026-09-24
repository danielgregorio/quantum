<q:component name="TestUploadNaming">
  <!-- Test: File upload with unique naming strategy -->

  <q:action name="uploadDocument" method="POST">
    <q:param name="file" type="file" required="true" />

    <q:file action="upload"
            file="{file}"
            destination="./uploads/documents/"
            nameConflict="makeUnique"
            result="uploadResult" />

    <!-- Expected: Unique filename generated (UUID-based) -->
    <q:flash message="File saved as: {uploadResult.filename}" type="success" />
  </q:action>

  <!-- Expected: Naming strategy configured -->
  Naming strategy: makeUnique (prevents conflicts)
</q:component>
