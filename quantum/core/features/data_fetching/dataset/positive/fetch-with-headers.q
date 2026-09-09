<?xml version="1.0" encoding="UTF-8"?>
<!--
Positive Example: Fetch with custom headers
Tests: Authentication and custom headers
-->
<q:component xmlns:q="https://quantum.lang/ns" name="fetch-with-headers">
    <q:set name="authToken" value="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." />

    <q:fetch name="profile" url="/api/profile" method="GET">
        <q:header name="Authorization" value="Bearer {authToken}" />
        <q:header name="X-API-Version" value="2.0" />
        <q:header name="Accept-Language" value="en-US" />

        <q:loading>Loading profile...</q:loading>
        <q:error>
            <div class="error">
                Unable to load profile. Please check your authentication.
            </div>
        </q:error>
        <q:success>
            <div class="profile-card">
                <h2>{profile.name}</h2>
                <p>Email: {profile.email}</p>
                <p>Role: {profile.role}</p>
            </div>
        </q:success>
    </q:fetch>
</q:component>
