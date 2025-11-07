# CSS Property Override Roadmap

This document tracks the future work required to support adding/removing arbitrary CSS properties (beyond colour overrides) when patching Unity StyleSheets.

## Goals

- Allow skin authors to add new declarations (e.g. `height`, `width`, layout properties) to existing selectors.
- Support removal or replacement of existing declarations (such as the built-in `color` values on attribute classes).
- Resolve `var(--foo)` references against skin-defined variables, including those introduced through `@import`ed files.
- Enable mapping-based scoping so locally defined variables and overrides can target specific Unity StyleSheet assets.
- Improve debug exports to reflect multi-value property tokens and resolved variables for easier verification.
- Maintain compatibility with current colour-only overrides and mapping behaviour.

## Supported Use Cases

This roadmap covers all of the requested authoring scenarios:

- **Local variable passthrough** – Declare variables in your skin CSS and reference them in selectors (`background-color: var(--my-accent);`).
- **Imported variable reuse** – Pull shared variables in via `@import "shared/colors.css";` and make them available to mapped assets.
- **Assigning existing bundle variables** – Point properties at bundle-provided tokens without converting them to literals when desired (e.g. keep `color: var(--club-primary);`).
- **Per-property overrides** – Add, replace, or remove individual declarations such as `background-color`, `flex-direction`, `padding`, `height`, etc.
- **Multi-value properties** – Author properties that require multiple tokens (`background-image: url(hero.png) | none;`, `transition: color 0.2s ease;`) and have them serialized faithfully into Unity's StyleSheet format.
- **Enhanced exports** – Ensure the debug `original_*.uss` / `patched_*.uss` exports display the multi-value tokens and variable references so authors can validate their changes.

## Implementation Plan

1. **Specification & parsing layer**
   - Formalise syntax for multi-value declarations, `!remove` / `!replace` flags, and `@import` handling (including resolution order).
   - Extend the CSS ingestion helpers to capture arbitrary declaration blocks (not just colours) and to inline imported files before parsing.
   - Record raw property tokens, including `var(--foo)` references and multi-value sequences, inside `CssFileOverrides`.

2. **Value normalisation & resolution**
   - Introduce converters that translate tokens into Unity StyleSheet value types (floats, enums/keywords, resource paths, colours, booleans).
   - Resolve variables by merging scopes in precedence order (asset-mapped > filename stem > global) and allow opting into literal conversion or string-handle preservation.
   - Handle unit parsing (px, %, em) and multi-token values (`url(...)`, gradients, comma/pipe separated sequences).

3. **Data model updates**
   - Expand `CssFileOverrides` and `CollectedCss` to carry per-selector/per-property add/replace/remove payloads, multi-value arrays, and variable resolution metadata.
   - Track imported file origins for diagnostics and to avoid double-processing the same variable declarations.
   - Preserve backward compatibility so colour-only skins continue to work without modifications.

4. **CssPatcher enhancements**
   - Teach `_apply_patches_to_stylesheet` to add or update `m_Properties` entries spanning colours, floats, enums, resource paths, and string references while allocating indices safely.
   - Implement property removal (`!remove`) by pruning the relevant `m_Properties` entries and, when safe, cleaning up unused array slots.
   - Support multi-value properties by writing multiple `m_Values` entries per property in the order supplied by the overrides.
   - Honour directives to keep variable references as string handles instead of forcing literal colour conversion when requested.

5. **Scan cache, targeting & exports**
   - Update scan-cache generation and candidate filtering to index the wider property set, multi-value sequences, and variable references; bump cache schema versions accordingly.
   - Enhance the debug export (`serialize_stylesheet_to_uss`) to surface multi-value tokens and to annotate whether a value originated from a literal, a variable, or an imported declaration.

6. **User experience & docs**
   - Document the new syntax: `@import`, variable scoping rules, multi-value notation, `!remove` semantics, and mapping.json interactions.
   - Provide validation warnings and dry-run diagnostics for unsupported property types or unresolved variables.
   - Consider feature flags or staged rollout toggles if we want to enable advanced behaviour gradually.

7. **Testing strategy**
   - Add focused unit tests covering add/replace/remove paths for multiple property types, variable resolution, imports, and multi-value serialization.
   - Include integration tests that round-trip actual bundles to confirm Unity still accepts the patched assets and that debug exports match expectations.
   - Add regression tests to guarantee colour-only skins (and existing mapping workflows) behave exactly as before.

## Status

- Colour overrides (hex/rgb/rgba) are already supported and normalised.
- Arbitrary property manipulation remains future work; this document captures the agreed roadmap for when we tackle it.
