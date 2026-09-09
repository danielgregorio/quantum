<q:component name="TestUploadBasic">
  <!-- Test: Basic file upload -->

  <q:action name="uploadFile" method="POST">
    <q:param name="document" type="file" required="true" />

    <q:file action="upload"
            file="{document}"
            destination="./uploads/"
            result="uploadResult" />

    <q:flash message="File uploaded: {uploadResult.filename}" type="success" />
  </q:action>

  <!-- Expected: File upload configured -->
  File upload action configured
</q:component>
