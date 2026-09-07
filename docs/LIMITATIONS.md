# Scope and limitations

- Local, user-supplied PDFs only. No paywall bypass, literature download service, hosted model, OCR, or publisher identity verification.
- Text extraction uses the PDF text layer. Scans can have no text, and a text layer can contain errors or an unexpected reading order. Figure rendering remains available.
- Digitization supports separable Cartesian linear/log10 axes with user-declared calibration. Automated color tracing supports a single-valued curve in each accepted image column. Multiple traces, vertical segments, legends, scatter-marker centers, broken axes, perspective distortion, and experimental error bars require explicit manual handling.
- Default uncertainty reflects declared localization assumptions only. It does not quantify uncertainty in the source experiment or conclusions.
- PDFs are limited to 100 MiB and 2000 pages; raster rendering to 25 million pixels per page. These bounds prevent common accidental oversized jobs; the PDF renderer should still run in an appropriately isolated environment when processing untrusted files.
- Exports retain bibliographic metadata and hashes but omit full source content. A complete review requires the local source store. User-supplied licenses and DOI metadata are assertions, not permissions or authenticity checks.
- Tests use controlled synthetic PDFs with known curves. Validation on representative domain papers, scans, layouts, and publisher exports is still needed before relying on unattended extraction.
