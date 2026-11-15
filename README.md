# LEMMY News Monitor

## Deploy
1. Create a GitHub repository and upload all files, including `.github/workflows/collect.yml`.
2. In GitHub, open **Actions → Collect daily robot news → Run workflow** once. Check that `news.json` updates.
3. Create a Cloudflare Pages project connected to the GitHub repository. Framework preset: **None**. Build command: `exit 0`. Output directory: `/` (repository root, if supported by project settings). Alternatively deploy the root as static assets with the Cloudflare Pages CLI.
4. Open the generated `*.pages.dev` URL.
5. GitHub Actions runs daily at 07:30 Korea time, but scheduling can be delayed. Changes pushed to the repository trigger Cloudflare Pages redeployment.

## Keyword editing
- For team-wide collection, edit `keywords.json` in GitHub and commit. The next scheduled workflow uses the new keywords.
- The webpage's keyword management is **browser-local only**; it does not change GitHub or the daily collector. Use "설정 JSON 내보내기" to export changes and upload the exported file as `keywords.json` to GitHub.
- Categories are keys in `keywords.json`; keywords are arrays of strings.

## Limitations
- Google News RSS is not a guaranteed or comprehensive news API. It may change or throttle access.
- Items link to Google News RSS article URLs, which generally redirect to the original publisher.
- This version collects titles, dates, sources, and links only; no AI summarization.
- The public Cloudflare Pages site has no authentication. Use access controls before adding private data.
- Daily collection only runs when GitHub Actions is enabled and has write permission; repository branch protection can prevent commits.
