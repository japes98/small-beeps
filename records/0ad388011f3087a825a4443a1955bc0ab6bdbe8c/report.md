# Test record 0ad388011f30

- Commit: `0ad388011f3087a825a4443a1955bc0ab6bdbe8c`
- Subject: Merge pull request #3 from japes98/m0b/setup
- Tree: `876d78f36b595bd536955b9285cf352568390bcc`
- Written: 2026-10-22T10:44:27Z
- Overall: **PASS**
- CI run: https://github.com/japes98/small-beeps/actions/runs/39765267081

## Checks

| Check | Title | Requirements | Result | Seconds |
|-------|-------|--------------|--------|---------|
| C-UNIT | Unit tests of the tools | R-PROC-1, R-PROC-4, R-REC-1, R-CLEAN-3, R-CLEAN-4, R-PUB-1, R-SEP-2 | PASS | 3.0 |
| C-REUSE | reuse lint (SPDX licence and copyright on every file) | R-LIC-1, R-LIC-2 | PASS | 0.7 |
| C-COMMIT-MSG | Commit messages follow .gitmessage | R-PROC-1 | PASS | 0.1 |
| C-LOW-PROFILE | Low profile: name, description, topics, README | R-PUB-1 | PASS | 0.3 |
| C-SECRETS | No secrets in tracked files | R-PUB-2 | PASS | 0.2 |
| C-NO-TOOLCHAIN | No toolchain parts or binaries tracked | R-REPRO-1 | PASS | 0.0 |
| C-DENY-LISTS | Claude Code deny lists never drop an entry | R-CLEAN-4, R-SEP-2 | PASS | 0.0 |
| C-TRANSCRIPTS | Archived session transcripts: banners and forbidden material | R-CLEAN-1, R-CLEAN-3, R-CLEAN-5, R-SEP-2 | PASS | 0.1 |
| C-SDK-PIN | Vendored SDK files match the pinned commit | R-REPRO-5, R-LIC-2 | PASS | 0.0 |
| C-IMAGE | Build container (pinned base, toolchain SHA-256 checked) | R-REPRO-1, R-REPRO-2 | PASS | 21.5 |
| C-BUILD-A | Build A in a fresh container (source at /mnt/small-beeps-src) | R-REPRO-3, R-BUILD-1 | PASS | 0.3 |
| C-BUILD-B | Build B in a fresh container (source at another path) | R-REPRO-3 | PASS | 0.2 |
| C-DETERMINISM | Builds A and B are byte-identical | R-REPRO-3 | PASS | 0.0 |
| C-MERGE | Signed owner merge of a pull request that passed CI | R-PROC-2 | PASS | 1.5 |

## Outputs

| File | SHA-256 |
|------|---------|
| `placeholder.elf` | `d244f5f69b8316cba91e93349118552b4aeed38205336a67a606780f27b0e1eb` |
| `placeholder.o` | `e979d19e666fcdc0ca0e71b5159634bf39a1d5283060ea59f98da8252cb04f9a` |

## Traceability

| Requirement | Checks | Result |
|-------------|--------|--------|
| R-PROC-1 | C-UNIT, C-COMMIT-MSG | PASS |
| R-PROC-2 | C-MERGE | PASS |
| R-PROC-3 | - | not machine-checked (review) |
| R-PROC-4 | C-UNIT | PASS |
| R-REC-1 | C-UNIT | PASS |
| R-REC-2 | - | not machine-checked (records.yml, ots-upgrade.yml) |
| R-REPRO-1 | C-NO-TOOLCHAIN, C-IMAGE | PASS |
| R-REPRO-2 | C-IMAGE | PASS |
| R-REPRO-3 | C-BUILD-A, C-BUILD-B, C-DETERMINISM | PASS |
| R-REPRO-4 | - | not machine-checked (review (run by hand; result in the PR)) |
| R-REPRO-5 | C-SDK-PIN | PASS |
| R-BUILD-1 | C-BUILD-A | PASS |
| R-LIC-1 | C-REUSE | PASS |
| R-LIC-2 | C-REUSE, C-SDK-PIN | PASS |
| R-PUB-1 | C-UNIT, C-LOW-PROFILE | PASS |
| R-PUB-2 | C-SECRETS | PASS |
| R-CLEAN-1 | C-TRANSCRIPTS | PASS |
| R-CLEAN-2 | - | not machine-checked (review) |
| R-CLEAN-3 | C-UNIT, C-TRANSCRIPTS | PASS |
| R-CLEAN-4 | C-UNIT, C-DENY-LISTS | PASS |
| R-CLEAN-5 | C-TRANSCRIPTS | PASS |
| R-SEP-1 | - | not machine-checked (review) |
| R-SEP-2 | C-UNIT, C-DENY-LISTS, C-TRANSCRIPTS | PASS |
| R-BOOT-1 | - | not machine-checked (planned (fwtest)) |
| R-BOOT-2 | - | not machine-checked (planned (fwtest)) |
| R-AUDIT-1 | - | not machine-checked (planned) |
| R-PERF-1 | - | not machine-checked (planned) |
| R-PERF-2 | - | not machine-checked (planned) |

## Environment

```json
{
  "build_image_id": "sha256:a15a1251de83e4b3d0d19f5c13c624a0a7ad0489ff8545fa60b962257510d53a",
  "build_image_tag": "small-beeps-build:2f1adc7009fddc03",
  "claude_configs": {
    "clean.json": "aafd506f4268023dc416bde494cced82cee18b0b4c8f4057d1652e8e86ca5119",
    "handmade-settings.json": "a557bd84008372ff9d3e24cd648df9986d76a05928d9f50b5d3e60975bf29b32",
    "spec.json": "eaa5f875583b21f3fcbb93b00bfbf8113dfc4b8d0cdb849df457a80ed542f810"
  },
  "docker": "client 28.0.4 server 28.0.4",
  "dockerfile": {
    "base": "debian:bookworm-slim@sha256:ec31d744f83f4a73447ba045aaab9409997efe5cc706eca4890c1be36cc1606a",
    "dockerfile_frontend": "docker/dockerfile:1.10@sha256:865e5dd094beca432e8c0a1d5e1c465db5f998dca4e439981029b3b81fb39ed5",
    "snapshot": "20261020T000000Z",
    "source_date_epoch": "1767225600",
    "toolchain_name": "jieli-linux-toolchains-20250324.1",
    "toolchain_sha256": "f686586bcfb45e0f0bb27fd2b39c7a7f313cb4f0e88a66a14da621ffa8225958",
    "toolchain_url": "https://jl-update.oss-cn-shenzhen.aliyuncs.com/jieli-linux-toolchains-20250324.1.tar.xz"
  },
  "git": "git version 2.55.0",
  "github": {
    "GITHUB_EVENT_NAME": "push",
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_REPOSITORY": "japes98/small-beeps",
    "GITHUB_RUN_ATTEMPT": "1",
    "GITHUB_RUN_ID": "39765267081",
    "GITHUB_SHA": "0ad388011f3087a825a4443a1955bc0ab6bdbe8c",
    "GITHUB_WORKFLOW": "records",
    "ImageOS": "ubuntu24",
    "ImageVersion": "20261021.345.10",
    "RUNNER_ARCH": "X64",
    "RUNNER_OS": "Linux"
  },
  "host": "Linux 7.0.0-1017-azure x86_64",
  "python": "3.12.15",
  "reuse": "reuse, version 6.2.0",
  "sdk_commit": "5fa84a9b2f723a5e9337ad79dc2ad741fc98fe2d",
  "sdk_sha256sums": "49ddeb5feab02203f64e14f581808fc8e84d9af858953dd76b8602c906a95fa6"
}
```
