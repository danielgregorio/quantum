<q:component name="TestUploadValidation">
  <!-- Test: File upload with validation (size and type) -->

  <q:action name="uploadAvatar" method="POST">
    <q:param name="avatar" type="file" required="true" />

    <q:file action="upload"
            file="{avatar}"
            destination="./uploads/avatars/"
            maxSize="5MB"
            allowedTypes="image/jpeg,image/png,image/gif"
            result="uploadResult" />

    <q:flash message="Avatar uploaded!" type="success" />
  </q:action>

  <!-- Expected: Validation rules (max 5MB, images only) -->
  File validation: max 5MB, images only (JPEG, PNG, GIF)
</q:component>
