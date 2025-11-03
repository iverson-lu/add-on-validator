# Bug Report - HP Add-on Catalog Analyzer Dashboard

**Report Date:** November 3, 2025  
**Tester:** QA Team  
**Environment:** Windows 11, Python 3.11, Chrome 130.0  
**Build Version:** Current development branch (remove-platform-column)

---

## Bug #1: Dashboard Charts Not Rendering

**Severity:** High  
**Priority:** P1  
**Status:** Open  

### Description
All statistical charts on the dashboard (Platform Distribution, Operating System Types, Architecture Distribution, and Annual Release Trends) fail to render when accessing the web interface. Instead of displaying pie charts, only empty white boxes are shown.

### Steps to Reproduce
1. Start the web application using: `python -m addon_catalog.webapp`
2. Navigate to `http://127.0.0.1:8000/` in a web browser
3. Wait for the page to fully load
4. Observe the "统计概览" (Statistics Overview) section

### Expected Result
Four pie charts should be displayed showing:
- Platform Distribution
- Operating System Types  
- Architecture Distribution
- Annual Release Trends

Each chart should render with colored segments representing the data distribution.

### Actual Result
All four chart containers display as blank white boxes. No data visualization appears. Browser console shows JavaScript errors related to JSON parsing.

### Error Messages
Browser Console Error:
```
无法解析图表数据 SyntaxError: Unexpected token 'i', "{invalid_json:"... is not valid JSON
```

### Impact
- Users cannot visualize distribution statistics
- Dashboard loses its primary value proposition
- Data analysis requires manual inspection of raw numbers
- Poor user experience for stakeholders reviewing catalog health

### Additional Information
- The metrics cards above the charts display correctly (total add-ons, platform count, etc.)
- The latest version list table below still functions properly
- Issue occurs on all tested browsers (Chrome, Firefox, Edge)
- Chart.js library loads successfully (verified via Network tab)

### Screenshots
[Chart area appears blank with white background and headers only]

---

## Bug #2: Missing "Architecture" Column Data in Latest Version List

**Severity:** Medium  
**Priority:** P2  
**Status:** Open

### Description
The "最新版本列表" (Latest Version List) table displays a header for the "架构" (Architecture) column, but the corresponding data cells in that column are completely empty. This creates a visual misalignment where there are more header columns than data columns.

### Steps to Reproduce
1. Start the web application using: `python -m addon_catalog.webapp`
2. Navigate to `http://127.0.0.1:8000/` in a web browser
3. Scroll down to the "最新版本列表" section at the bottom of the page
4. Examine the table structure and data

### Expected Result
The table should display 5 columns with aligned headers and data:
1. 描述 (Description) - with data
2. 最新版本 (Latest Version) - with data
3. 操作系统 (Operating System) - with data
4. **架构 (Architecture) - with data** ← Missing
5. 发布日期 (Release Date) - with data

Example expected row:
| Description | Version | OS | Architecture | Release Date |
|------------|---------|-----|--------------|--------------|
| HP USB... | 2.1.3 | Win10x64 | **x64** | 2024-08-15 |

### Actual Result
The table displays 5 column headers but only 4 data columns per row:
1. 描述 (Description) - ✓ has data
2. 最新版本 (Latest Version) - ✓ has data
3. 操作系统 (Operating System) - ✓ has data
4. **架构 (Architecture) - ✗ NO DATA (empty cells)**
5. 发布日期 (Release Date) - but appears in the wrong column

The data appears to be shifted - release dates now appear under the architecture column header, making the actual release date column empty.

### Impact
- Table data alignment is broken
- Users cannot determine the architecture requirements for add-ons
- Filtering by architecture is essentially useless as users can't see what architecture each item supports
- Data integrity appears compromised, reducing trust in the dashboard
- Critical information for system compatibility is missing

### Additional Information
- The architecture filter dropdown still works and shows available options (x64, x86, etc.)
- The metrics card showing architecture count displays correctly
- When filtering by architecture, items are filtered but still show no architecture data
- The table header shows all 5 columns correctly
- Issue appears to be in the table row rendering, not in data fetching

### Data Verification
Verified that the source XML contains architecture information. The issue appears to be in the web rendering layer only.

### Visual Impact
```
Current (Broken):
┌─────────────┬─────────┬───────────┬────────────┬─────────────┐
│ Description │ Version │    OS     │Architecture│Release Date │ ← Headers
├─────────────┼─────────┼───────────┼────────────┼─────────────┤
│ HP USB...   │ 2.1.3   │ Win10x64  │            │             │ ← Misaligned data
│ HP Network..│ 1.5.0   │ Win10x64  │ 2024-08-15 │             │ ← Date in wrong column
└─────────────┴─────────┴───────────┴────────────┴─────────────┘

Expected (Correct):
┌─────────────┬─────────┬───────────┬────────────┬─────────────┐
│ Description │ Version │    OS     │Architecture│Release Date │ ← Headers
├─────────────┼─────────┼───────────┼────────────┼─────────────┤
│ HP USB...   │ 2.1.3   │ Win10x64  │    x64     │ 2024-08-15  │ ← All aligned
│ HP Network..│ 1.5.0   │ Win10x64  │    x64     │ 2024-08-12  │ ← All aligned
└─────────────┴─────────┴───────────┴────────────┴─────────────┘
```

---

## Test Environment Details
- **Operating System:** Windows 11 Pro (Build 22631)
- **Python Version:** 3.11.5
- **Browser:** Google Chrome 130.0.6723.92
- **Also Tested:** Firefox 121.0, Microsoft Edge 130.0
- **Screen Resolution:** 1920x1080
- **Server:** Development HTTP server (http.server)

## Reproduction Rate
**Bug #1:** 100% (occurs on every page load)  
**Bug #2:** 100% (occurs on every page load)

## Suggested Fix Areas
**Bug #1:** Investigate the `_build_chart_payload()` function in `webapp.py` - likely JSON serialization issue  
**Bug #2:** Check the `_render_versions()` function in `webapp.py` - table cell generation appears to skip architecture column

## Attachments
- N/A (visual bugs, descriptions provided above)

---

**Report Prepared By:** QA Testing Team  
**Next Steps:** Assign to development team for investigation and fix
