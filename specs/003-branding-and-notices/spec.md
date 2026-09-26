# Feature Specification: Branding and notices

**Feature Branch**: `003-branding-and-notices`
**Created**: 2026-09-26
**Status**: Specified
**Input**: Roadmap slice 3: one product identity, MikroCAM title/About, preserved FlatCAM/Evo
credits, MIT license and complete dependency notices including PyQt6 GPLv3.

## User Scenarios & Testing

### User Story 1 - Identify the application (Priority: P1)

As a user, I want the title, About and application information to identify MikroCAM consistently
and direct me to its project while retaining credit to its upstream authors.

**Why this priority**: Users must know which fork and version they are running.
**Independent Test**: Launch the application, open About, save/reopen a project and inspect the title.
**Acceptance Scenarios**:
1. Given a clean launch, when I inspect the title and About, then the same product name/version appears.
2. Given a reopened project, when its name is added to the title, then MikroCAM identity remains intact.
3. Given About, when I inspect project links and credits, then links target MikroCAM and the original
   FlatCAM and Evo copyright holders remain clearly identified.

### User Story 2 - Read licensing and provenance (Priority: P1)

As a recipient, I want the application's source license and third-party notices available together,
so I can identify which terms belong to which component.

**Why this priority**: A public source release needs accurate attribution and license boundaries.
**Independent Test**: Compare the dependency inventory to every pinned requirement and verify each
notice file against its recorded source hash.
**Acceptance Scenarios**:
1. Given the source checkout, when I read LICENSE and NOTICE, then MikroCAM's MIT terms and
   FlatCAM/Evo copyrights are preserved, and dependency terms are distinguished.
2. Given core, development and optional image pins, when I inspect the inventory, then each version
   has its license metadata and the available full upstream license/notice texts.
3. Given PyQt6 and other copyleft dependencies, when I inspect notices, then their supplied license
   terms remain visible and are not represented as relicensed under MIT.

### User Story 3 - Preserve existing data and product boundaries (Priority: P2)

As an existing user, I want branding to preserve my projects and tool settings and avoid offers
to replace MikroCAM with a different upstream application.

**Why this priority**: Display identity must not change the host's data compatibility identifiers.
**Independent Test**: Run the CAM project round-trip and exercise update entry points without network access.
**Acceptance Scenarios**:
1. Given an existing project or tools database, when used with MikroCAM branding, then existing host
   compatibility versions and storage paths remain unchanged.
2. Given inherited update preferences or a manual update request, when launched through MikroCAM,
   then no Evo download/install is offered; product update controls are unavailable with a clear explanation.

### Edge Cases

- A project name can contain markup; display helpers must preserve it as text.
- Optional image packages are absent during ordinary startup.
- Wheel metadata may lack a complete license; retrieve the exact upstream version's notice instead
  of inventing one. Bundled binary notices and source-vendored code also need attribution.
- Existing asset credits with incomplete per-file provenance must remain attributed and their
  unresolved provenance stated explicitly, rather than asserting a new license for those assets.
- Old automatic-update settings cannot re-enable a product channel that has not been configured.

## Requirements

### Functional Requirements

- **FR-001**: Product name, version, links and About identity MUST have one authoritative definition.
- **FR-002**: Initial/reopened window titles, About and product information MUST use that definition.
- **FR-003**: FlatCAM and Evo copyrights, authors and applicable source credits MUST be preserved.
- **FR-004**: MIT LICENSE and NOTICE MUST distinguish application source from dependencies/assets.
- **FR-005**: All pinned core/development/optional image dependencies MUST have a versioned inventory
  and source-traceable full package license texts, including all bundled notices supplied with
  those distributions. Missing notices for embedded native libraries MUST be explicitly recorded
  as unresolved binary-distribution audit items, never represented as cleared by the package license.
- **FR-006**: Dependency notice completeness and product consistency MUST be automatically checked.
- **FR-007**: Existing project format, compatibility version, settings namespace and tool storage MUST remain unchanged.
- **FR-008**: MikroCAM update entry points MUST NOT use Evo's update channel; no replacement updater is introduced.

### Key Entities

- Product identity: displayed name/version, description, official links, copyright and upstream attribution.
- Dependency record: normalized package name, pinned version, install group, license metadata,
  source/version and copied notice paths with integrity hashes.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All inspected product identity surfaces agree on name and version after launch and reopen.
- **SC-002**: 100% of pinned dependencies have an inventory entry and at least one complete license text.
  Supplied bundled notices are preserved; this measures source-checkout notice coverage, not
  clearance to redistribute every optional native library or inherited artwork.
- **SC-003**: The existing CAM round-trip preserves all four objects and generated G-code; full tests and guards pass.
- **SC-004**: Update entry-point tests produce zero upstream update network calls or installer launches.

## Assumptions

- Features 001 and 002 supply the validated baseline and guardrails. No CAM algorithm changes.
- MikroCAM initial version is 0.1.0. Host compatibility identifiers are distinct from display identity.
- Installer/binary distribution is a later roadmap slice; downloaded browsers are not vendored here.
- Existing bundled icons keep upstream credits; incomplete asset provenance is recorded for release audit.
