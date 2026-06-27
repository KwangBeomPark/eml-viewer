# EML Viewer

English | [한국어](README.ko.md)

EML Viewer is a Windows-first desktop app for opening `.eml` email files with a layout that behaves like a normal desktop window and renders HTML email bodies with Qt WebEngine.

## Why This Exists

I started this project because the default email viewer I used at work did not behave well with Windows window snapping shortcuts such as `Win + Left` and `Win + Right`. What began as a small viewer for reading email files has gradually become a convenience-focused alternative to the default email reader: easier window handling, clearer metadata, readable plain text and HTML views, inline image rendering, and attachment saving.

This is an open project. The documentation intentionally avoids company names, internal system names, real email content, and other confidential details.

## Features

- Open a single `.eml` file from the app or from a file association.
- Display subject, sender, recipients, and date.
- Show Plain Text and HTML body tabs.
- Render HTML email with Qt WebEngine for better table, CSS, and inline image support.
- Resolve embedded `cid:` images, `Content-Location` images, relative image paths, CSS `url(...)`, and `srcset` references.
- Block remote images by default and let the user enable them for the current message.
- Show and save attachments.
- Preserve the last window size and position.
- Check GitHub Releases for updates.
- Show user-friendly error dialogs instead of closing unexpectedly.

## Install For General Use

The Windows installer is intended for users who do not have Python installed.

1. Download and run `EmlViewerSetup-<version>.exe`.
2. Keep the file association option enabled if you want `.eml` files to open with EML Viewer.
3. After installation, launch `EML Viewer` from the Start menu or double-click an `.eml` file.

## Development Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Run the app:

```powershell
python -m eml_viewer
```

Open a sample file directly:

```powershell
python -m eml_viewer .\samples\example_plain_text.eml
```

Run tests:

```powershell
python -m unittest discover -s tests
```

## Build

Build the Windows app folder:

```powershell
python -m pip install -e ".[build]"
.\scripts\build_windows.ps1
```

The output is created in `dist\EmlViewer`.

Build the Windows installer:

```powershell
python -m pip install -e ".[build]"
.\scripts\build_installer.ps1
```

Inno Setup 6 is required for the installer. The output is created in `installer\`.

## Design Notes

- UI code and email parsing logic are kept separate.
- `EmlParser` parses the message and classifies attachments versus inline resources.
- `MessageBodyWidget` prepares HTML resources and renders the body.
- HTML rendering uses Qt WebEngine because accurate email body rendering is more important than keeping the package as small as possible.
- Remote images are blocked by default to reduce tracking and privacy risk.
- Attachment saving follows a preview, confirm, execute flow.

## Privacy And Public Repository Notes

- Do not commit real email files, company data, internal URLs, credentials, or customer information.
- The included sample uses `example.com` addresses only.
- Before publishing a release, scan tracked files for secrets or confidential strings.

Useful checks:

```powershell
git grep -n -I -i -E "api[_-]?key|secret|token|password|credential|client_secret|private key|confidential|internal|proprietary" -- .
git grep -n -I -E "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|https?://" -- .
```
