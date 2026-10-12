# Use Supabase Postgres with the CRM

The CRM uses Django's ORM, so Supabase is configured as its PostgreSQL database.
The app server connects to Postgres directly; the Supabase client libraries and
Data API are not needed.

## Configure Render

1. Create a Supabase project, preferably in a region close to the Render service.
2. In Supabase, open **Connect** and copy the **Session pooler** connection
   string. Render services use IPv4, while Supabase's direct database endpoint
   may require IPv6. Session mode supports IPv4 and persistent server processes.
3. In the Render web service's environment settings, add:

   - `SUPABASE_DB_URL`: the full session-pooler URI copied from Supabase
   - `DATABASE_SSL_REQUIRE`: `true`

   Keep the URI private. Do not commit it to Git or put it in frontend code.
4. Deploy the branch configured for the Render service. The repository's
   `build.sh` runs `python manage.py migrate`, which creates/updates the schema
   in Supabase during the build.

The URI format shown by Supabase is similar to:

```text
postgresql://postgres.<project-ref>:<database-password>@<pooler-host>:5432/postgres
```

Use the actual host and username from Supabase's Connect panel. If the database
password contains reserved URL characters, URL-encode them before inserting it
in the URI.

## Local development

Add `SUPABASE_DB_URL` to `crm_project/.env` to connect locally. When it is
unset, Django continues to use the local SQLite database. `DATABASE_URL` remains
supported as a fallback.

## Existing CRM data

Changing the connection does not copy records from SQLite or Render's current
database. After configuring Supabase, the app will use the new database, which
starts with an empty schema/data set apart from anything created by deployment
commands. Export and import the existing users, employees, attendance, and
leave data separately if those records need to be retained. Take a backup of
the source database before doing that migration.

Supabase connection guidance: [Connect to Postgres](https://supabase.com/docs/guides/database/connecting-to-postgres).
