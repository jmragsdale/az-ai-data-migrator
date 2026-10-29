# README artwork

This README follows the navy, teal, neutral surfaces and DIN Alternate display typography of [Jermaine Ragsdale’s profile](https://github.com/jmragsdale). The header has a mobile variant; navigation cards have light and dark variants and wrap on smaller screens. Alt text and ordinary links expose the same destinations.

PNG exports preserve typography across devices. SVG sources and `artwork.json` retain editable text and labels. Current exports use the macOS DIN Alternate system font; no font files are redistributed. Arial Narrow or Arial are used where that font is unavailable. Viewing the README requires no external image or font service.

To regenerate, install Sharp in a temporary build environment (`npm install --no-save sharp`) and run `node tools/build-readme-art.cjs` from the repository root. Review the PNG exports and update README links and alt text when changing labels or destinations. The artwork build does not execute application tests or deploy infrastructure. The scoped `.gitattributes` rules classify the artwork and build helper as documentation for GitHub language statistics.
