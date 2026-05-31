# Deployment Guide

## 1. Overview

QC Enterprise can be deployed using Vercel for application hosting, Supabase for PostgreSQL database and storage, and Google Apps Script for Google Sheets export integration.

This deployment model keeps the system practical for a student project, portfolio, thesis demonstration, and early production use. Vercel handles public web access, Supabase stores operational data and uploaded evidence files, while Google Apps Script acts as a webhook bridge between the application and Google Sheets.

## 2. Deployment Architecture

The deployment architecture includes the following components:

- **Frontend static files:** HTML, CSS, JavaScript, assets, and PWA files served through Vercel.
- **Flask API:** Backend API routes for authentication, monitoring, batch production, QC inspection, reports, learning, audit, and export workflows.
- **Supabase PostgreSQL:** Main relational database for users, products, batches, monitoring logs, QC reports, audit logs, and learning data.
- **Supabase Storage:** Storage bucket for evidence photos and uploaded QC documentation.
- **Google Apps Script Webhook:** Web App endpoint that receives export payloads from the backend.
- **Google Sheets Export:** Spreadsheet output for monitoring, QC, and historical re-export data.
- **PWA:** Progressive Web App support through manifest, icons, and service worker.

## 3. Required Accounts

Prepare the following accounts before deployment:

- GitHub.
- Vercel.
- Supabase.
- Google Account.

The GitHub repository is used as the source for deployment. Vercel connects to the repository and deploys the app. Supabase provides the database and storage. Google Account access is required to create Google Sheets and deploy Google Apps Script.

## 4. Environment Variables

Environment variables must be configured in Vercel and should not be exposed in frontend code.

Required variables:

```text
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
JWT_SECRET
GOOGLE_APPS_SCRIPT_WEBHOOK_URL
FLASK_ENV
APP_ENV
```

Notes:

- `SUPABASE_URL` points to the Supabase project URL.
- `SUPABASE_ANON_KEY` is used for public-safe Supabase access when appropriate.
- `SUPABASE_SERVICE_ROLE_KEY` is sensitive and must only be used on the backend.
- `JWT_SECRET` must be a strong secret value used for authentication signing.
- `GOOGLE_APPS_SCRIPT_WEBHOOK_URL` should use the deployed Apps Script `/exec` URL.
- `FLASK_ENV` or `APP_ENV` identifies the runtime environment, such as `production`, `staging`, or `development`.

Do not commit real secret values to GitHub.

## 5. Supabase Setup

Recommended Supabase setup steps:

1. Create a new Supabase project.
2. Run database migrations.
3. Set up required tables for users, products, production batches, monitoring logs, QC reports, audit logs, learning data, and export logs.
4. Set up a storage bucket for evidence photos.
5. Apply database policies and storage policies.
6. Seed demo account data for testing and presentation.

Storage bucket recommendation:

```text
evidence-photos
```

Security recommendations:

- Restrict write access to authenticated users.
- Validate file type and file size before upload.
- Keep service role access limited to backend operations.
- Avoid using service role credentials in frontend JavaScript.

## 6. Vercel Setup

Recommended Vercel deployment steps:

1. Connect the GitHub repository to Vercel.
2. Configure build and output settings based on the project structure.
3. Set all required environment variables in Vercel.
4. Deploy the project.
5. Redeploy after changing environment variables.
6. Check Vercel logs for startup, route, API, and integration errors.

Important notes:

- Vercel does not automatically apply updated environment variables to an existing deployment.
- After adding or changing environment variables, trigger a redeploy.
- Use deployment logs to inspect Flask API errors, missing environment variables, and integration failures.

## 7. Google Apps Script Setup

Google Apps Script is used as the webhook receiver for Google Sheets export.

Recommended setup steps:

1. Create a Google Sheet for QC Enterprise export data.
2. Open Extensions > Apps Script.
3. Create an Apps Script project.
4. Add a `doPost(e)` function to receive webhook payloads.
5. Deploy the script as a Web App.
6. Set execution identity to **Execute as Me**.
7. Set access to **Anyone** or **Anyone with link**, depending on the required access model.
8. Copy the deployed Web App `/exec` URL.
9. Add the `/exec` URL to Vercel as `GOOGLE_APPS_SCRIPT_WEBHOOK_URL`.
10. Redeploy the Vercel project.

Basic webhook shape:

```javascript
function doPost(e) {
  const payload = JSON.parse(e.postData.contents);
  return ContentService
    .createTextOutput(JSON.stringify({ success: true, received: payload.type }))
    .setMimeType(ContentService.MimeType.JSON);
}
```

Use the `/exec` URL for production webhook requests. The `/dev` URL should only be used for testing during script development.

## 8. PWA Setup

PWA support requires the following files and assets:

- `manifest.json`.
- App icons in required sizes.
- Service worker file.
- Correct HTML references to the manifest and service worker.

Validation checklist:

- Manifest loads successfully.
- Icons are available and correctly sized.
- Service worker registers without console errors.
- The app can be added to home screen on supported devices.
- Installed mode opens in standalone display when configured.

## 9. Post-Deployment Checklist

After deployment, verify the following workflows:

- [ ] Login as admin.
- [ ] Login as staff.
- [ ] Submit monitoring.
- [ ] Submit QC.
- [ ] Create batch.
- [ ] Open reports.
- [ ] Test Google Sheets export.
- [ ] Test PWA install.

These checks confirm that authentication, database writes, external integration, reporting, and mobile installation behavior are working in the deployed environment.

## 10. Common Issues

### Google Sheets Export Returns 302 or 405

Use the Apps Script Web App `/exec` URL instead of an edit, preview, or `/dev` URL. Also confirm that the Web App is deployed with the correct access settings.

### Environment Variables Not Updated Until Redeploy

Vercel deployments use environment variables captured at deployment time. Redeploy the project after changing any environment variable.

### Supabase Migration Not Applied

If tables or columns are missing in production, confirm that migrations were applied to the correct Supabase project.

### Storage Upload Failure

Check Supabase Storage bucket name, policies, file size, file type validation, and backend credentials.

### Route Download Issue from Extensionless Files

Some static hosting or route configurations may treat extensionless files as downloads. Confirm routing rules, content type headers, and static file configuration.

### CORS or CSP Issue

Check allowed origins, API route configuration, security headers, and external script or webhook access.

## 11. Rollback Strategy

Recommended rollback options:

- Use `git revert` to create a clean rollback commit for application code.
- Restore a previous Vercel deployment from the Vercel dashboard.
- Treat database rollback with caution because schema changes can affect existing data.

Database migration caution:

- Avoid destructive schema changes in production.
- Back up production data before major migrations.
- Test rollback and forward migration plans before release.
- Prefer additive migrations whenever possible.

## 12. Production Recommendations

For more reliable production operation:

- Use a custom domain.
- Separate demo and production databases.
- Back up the database regularly.
- Restrict demo account permissions and avoid using real admin credentials for public demos.
- Monitor Vercel, Supabase, and Google Apps Script logs.
- Secure the Supabase service role key and keep it backend-only.

Operational recommendations:

- Rotate secrets if they are exposed.
- Use strong passwords for demo and admin accounts.
- Keep production environment variables separate from local development values.
- Review Google Sheets sharing permissions before public demonstrations.

## 13. Future Deployment

Future deployment improvements can make QC Enterprise more scalable and production-ready.

Potential directions:

- Custom domain for professional access and presentation.
- Android APK packaging with Capacitor.
- Multi-tenant SaaS deployment for multiple kitchens, branches, or organizations.
- IoT sensor integration for automated temperature monitoring.

These improvements can support a transition from a portfolio-grade web system into a broader quality control automation platform.
