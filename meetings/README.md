# Board meeting workspaces

Create a private, dated workspace from the repository root:

```bash
make new MEETING=2026-09-20
```

Drop the Sage 50 `.xlsx` exports into the new meeting's `source/` folder, then
edit `report.yaml`. Check and build the package with:

```bash
make doctor MEETING=2026-09-20
make report MEETING=2026-09-20
```

The dated folders are ignored by git because they contain financial records and
board notes. Generated HTML and PDF files are written into the meeting's
`output/` folder.
