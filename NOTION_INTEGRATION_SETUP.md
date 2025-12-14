# Notion Integration Setup Instructions

This guide walks you through creating a Notion integration for Scholia to enable exporting paper insights to your Notion workspace.

## Step 1: Create a Notion Integration

1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **"+ New integration"**
3. Fill in the integration details:
   - **Name**: `Scholia` (or any name you prefer)
   - **Associated workspace**: Select your workspace
   - **Type**: Select **"Public integration"** (required for OAuth)
   - **Logo** (optional): Upload a logo if desired

4. Click **"Submit"** to create the integration

## Step 2: Configure OAuth Settings

After creating the integration, you'll be taken to the integration settings page.

1. In the **"OAuth Domain & URIs"** section:
   - **Redirect URIs**: Add `http://localhost:8000/api/notion/callback`
   - Click **"Add URI"** to save

2. In the **"Capabilities"** section, ensure these are enabled:
   - ✅ Read content
   - ✅ Update content
   - ✅ Insert content

3. In the **"Content Capabilities"** section, enable:
   - ✅ Read pages
   - ✅ Update pages
   - ✅ Insert pages

## Step 3: Get Your Credentials

1. Copy the **OAuth client ID** - you'll see this in the OAuth section
2. Click **"Show"** next to "OAuth client secret" and copy it
3. Keep this page open or save these values securely

## Step 4: Add to Environment Variables

Add these to your `.env` file in the project root:

```bash
# Notion Integration
NOTION_CLIENT_ID=your_client_id_here
NOTION_CLIENT_SECRET=your_client_secret_here
NOTION_REDIRECT_URI=http://localhost:8000/api/notion/callback
```

Replace `your_client_id_here` and `your_client_secret_here` with the values from Step 3.

## Step 5: Grant Access to Your Pages

When you first use the Notion integration in Scholia:

1. Click "Add to Notion" in the Scholia interface
2. You'll be redirected to Notion's authorization page
3. **Select which pages to share** with Scholia
   - You can grant access to specific pages or your entire workspace
   - For research projects, grant access to pages containing your Literature Reviews
4. Click **"Select pages"**
5. Choose the specific pages you want Scholia to access
6. Click **"Allow access"**

You'll be redirected back to Scholia with authorization complete.

## Troubleshooting

### "Invalid redirect_uri" Error
- Ensure the redirect URI in your Notion integration settings exactly matches: `http://localhost:8000/api/notion/callback`
- No trailing slashes
- Must use `http://` (not `https://`) for localhost

### "Integration not found" Error
- Verify your `NOTION_CLIENT_ID` in `.env` matches the OAuth client ID from Notion
- Make sure you're using the OAuth client ID, not the Internal Integration Token

### Can't See My Pages
- Make sure you granted access to the specific pages during OAuth authorization
- You can update page access anytime at: Settings & members → Connections → Scholia

### Access Token Issues
- If you need to re-authorize, delete the `NOTION_ACCESS_TOKEN` from your `.env` file
- Click "Add to Notion" again to go through OAuth flow

## Security Notes

- The OAuth access token is stored in your `.env` file (single-user setup)
- Never commit your `.env` file to version control
- Keep your client secret private
- You can revoke access anytime from Notion's integration settings

## Next Steps

After setup is complete, you can:
1. Click "Add to Notion" on any session with extracted insights
2. Select your research project
3. Review the suggested relevance and theme
4. Export to your Notion Literature Review

## Support

For Notion API documentation, see:
- [Notion API Reference](https://developers.notion.com/reference/intro)
- [OAuth Public Integration Guide](https://developers.notion.com/docs/authorization)
