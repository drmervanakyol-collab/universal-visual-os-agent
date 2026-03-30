# Repo Inventory

- Generator: `ObserveOnlyRepoInventoryGenerator`
- Schema: `repo_inventory_v1`
- Repo root: `C:/Users/Mervan/Documents/GitHub/universal-visual-os-agent`
- Total files: `274`

## Summary Counts

### Primary Role
- `actions`: 6
- `ai_contracts`: 9
- `core`: 50
- `diagnostic`: 4
- `docs`: 7
- `runtime`: 8
- `scenario`: 7
- `semantics`: 17
- `support`: 126
- `test_only`: 40

### Production Criticality
- `critical`: 35
- `non_production`: 173
- `supporting`: 66

### Cleanup Recommendation
- `keep`: 75
- `retain_as_diagnostic_only`: 4
- `retain_as_test_only`: 40
- `review_for_archive`: 117
- `review_for_cycle_isolation`: 8
- `review_for_split`: 30

## Code Hygiene Hotspots

| Path | Primary Role | Criticality | Cleanup | Flags | Risk Notes |
| --- | --- | --- | --- | --- | --- |
| `docs/NEXT_STEPS.md` | docs | non_production | review_for_archive | archive | - |
| `docs/PROJECT_STATUS.md` | docs | non_production | review_for_archive | archive | - |
| `src/universal_visual_os_agent/actions/dry_run.py` | actions | supporting | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/actions/interfaces.py` | actions | supporting | review_for_cycle_isolation | - | cycle_member, high_internal_import_count:9, high_cross_package_import_count:5 |
| `src/universal_visual_os_agent/actions/safe_click.py` | actions | supporting | review_for_cycle_isolation | - | cycle_member, oversized_module, high_cross_package_import_count:5 |
| `src/universal_visual_os_agent/actions/scaffolding.py` | actions | supporting | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/ai_architecture/arbitration.py` | ai_contracts | supporting | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/ai_architecture/contracts.py` | ai_contracts | supporting | review_for_split | - | oversized_module, high_cross_package_import_count:5 |
| `src/universal_visual_os_agent/ai_architecture/ontology.py` | ai_contracts | supporting | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/ai_boundary/models.py` | ai_contracts | supporting | review_for_split | - | oversized_module, high_cross_package_import_count:4 |
| `src/universal_visual_os_agent/ai_boundary/validation.py` | ai_contracts | supporting | review_for_split | - | oversized_module, high_cross_package_import_count:5 |
| `src/universal_visual_os_agent/app/orchestration.py` | core | supporting | review_for_split | - | oversized_module, high_internal_import_count:10, high_cross_package_import_count:7 |
| `src/universal_visual_os_agent/integrations/windows/capture.py` | runtime | critical | review_for_split | - | oversized_module, high_internal_import_count:8 |
| `src/universal_visual_os_agent/integrations/windows/capture_backends.py` | runtime | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/capture_dxcam.py` | runtime | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/capture_gdi.py` | diagnostic | non_production | retain_as_diagnostic_only | diagnostic | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/capture_models.py` | runtime | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/capture_printwindow.py` | diagnostic | non_production | retain_as_diagnostic_only | diagnostic | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/dxcam_capture_diagnostic.py` | diagnostic | non_production | retain_as_diagnostic_only | diagnostic | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/foreground_capture_diagnostic.py` | diagnostic | non_production | retain_as_diagnostic_only | diagnostic | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/screen_metrics.py` | runtime | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/scenarios/action_flow.py` | scenario | supporting | review_for_split | - | oversized_module, high_internal_import_count:13, high_cross_package_import_count:8 |
| `src/universal_visual_os_agent/scenarios/definition.py` | scenario | supporting | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/scenarios/loop.py` | scenario | supporting | review_for_split | - | oversized_module, high_internal_import_count:9, high_cross_package_import_count:4 |
| `src/universal_visual_os_agent/scenarios/models.py` | scenario | supporting | review_for_split | - | oversized_module, high_internal_import_count:8, high_cross_package_import_count:4 |
| `src/universal_visual_os_agent/scenarios/state_machine.py` | scenario | supporting | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/building.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/candidate_exposure.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/candidate_generation.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/candidate_scoring.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/interfaces.py` | semantics | critical | review_for_cycle_isolation | - | cycle_member, high_internal_import_count:11 |
| `src/universal_visual_os_agent/semantics/layout_region_analysis.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/ocr.py` | semantics | critical | review_for_cycle_isolation | - | cycle_member, oversized_module |
| `src/universal_visual_os_agent/semantics/ocr_enrichment.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/ocr_rapidocr.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/preparation.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/semantic_delta.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/semantic_layout_enrichment.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/state.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/testing/repo_inventory.py` | support | supporting | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/verification/explanations.py` | core | supporting | review_for_cycle_isolation | - | cycle_member, oversized_module |
| `src/universal_visual_os_agent/verification/goal_oriented.py` | core | supporting | review_for_cycle_isolation | - | cycle_member, oversized_module |
| `src/universal_visual_os_agent/verification/interfaces.py` | core | supporting | review_for_cycle_isolation | - | cycle_member |
| `src/universal_visual_os_agent/verification/models.py` | core | supporting | review_for_cycle_isolation | - | cycle_member |

## Archive / Temp Candidates

| Path | Primary Role | Criticality | Cleanup | Flags | Risk Notes |
| --- | --- | --- | --- | --- | --- |
| `.tmp_test_artifacts/0089eed4a00f4f4e90225eadbec04665/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/047ac50140014bee8c64506c3020430a/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/0789d2025f244764bd4e3031309fba08/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/079b72f236224b08a52077f68c832f31/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/0d7be4de55a247cda0398d84320b0be0/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/0d88702574ec4174a30676bf8b1598d6/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/0e20dfc6fac248e7983e133ad4b72f32/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/10c3ae108d3d4238902b56eaca3c0ea5/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/1187b27d80b445d59cfed00297eb3d24/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/1201655668ca49dc9ad2c5edef14bd4d/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/1218f54081ad492a9579a876ec6fe10c/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/1496161461a047f680c8c84a6f6dcdc4/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/14ee3048239f4df59da5d0af2d5331c4/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/1cbe4b2cef0842809ed553d348ef921d/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/1fb9a8bafa6d4c499df31509c55db25d/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/21006d80acd440a1bf5dc27711cc69f1/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/2128506b72c34098bd28ed456ccd64e4/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/216c96a61eda45259a97d3d44478c219/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/26bf76693fb540c88a863fe56efc9d38/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/27f4e5c243654ff7a6743a4ce71d7afa/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/2852fa5876794fb1b1445927875a5487/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/2998d397034c4b27aeca319b2fb40b66/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/2d8028e7ac214a9bacc9732e905e8113/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/318c623f0fbe42908bb5731e6aaa1426/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/353a02087c804c7a9d62924890d26a82/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/375b8e04e06b4bad9f8ece63b2503b87/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/3b840c4b34944e77a10df665071bfed1/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/3cc6bed165b94c39b1aa7c2c51adde83/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/3ceb28537a8247ec946be68f46911f6f/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/3d5b44c7eb584b23b490097e36df1380/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/3f2da13e45394126892bdcd4ceda17a8/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/420ac1d92c8c4449a88b033a37e595ad/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/49778acd788940b3bb4a5b5224369891/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/4a62183db98f437ebe79c3fbd992ebc0/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/4f896fff0d39447380c78a7f53954142/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/4ff50a16ca0f48bf8f1687b3beec0c04/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/50073916e4294117b8c13be18ea6095b/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/52e67399c26c4e10a059880882d8437e/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/56557fe49fdb495091631709e1862862/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/5bc4ff6ffafa42b2976e2817701b1656/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/5d9c0aacf5f545c58a461900d5f83c84/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/5f55d0045be74b1195797482b3e0d337/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/605e33abfb36499d8fc04a782685939c/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/6116eb70770b42dd927c826b9d6dd47e/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/6278de17782e4f4c917ff3abf94581b9/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/633dae1d99f34f7e9d05dd0a6aff922e/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/6480a83a30044622ac84f3938bc3142e/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/66c407f5109b45e69649975555dbbed8/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/684e76c264344459ae1a65aaada283a2/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/696e525e58a8431e99028570e01bc548/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/69d3723a04484457a0685d935cabad58/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/6cb1e6d6dbb44486b15a1ed6a12886f5/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/7016729db8ca42448994eab129ca6a1a/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/71fd8e15a0a045ce995625334db3bb77/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/73957570a910427885f40bb7917975ea/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/73f3d4202e6b49d596092cf0fe34e8d1/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/7400b80e47e44d1fb6ebaf6eac3b72a9/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/742df26d3e11487fb1b07a7e86fdba41/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/754b9946442d4eef9a9086ff501dedbb/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/7945d243fd3d49e1bc972ad306bbe1b1/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/79d8010e25e541bd92eb806580e494e9/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/82a1c46645314128b9ecf1951932b3bb/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/83893ba038a546799336d63bf7916ebf/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/86c3c0dabec5401c89158a8671d558ba/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/8d489f88d2d04b5fa42edce4941ebd61/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/8f2cc5875a52476b85bddbb1c4e482bd/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/901098bf301646bb8182dc188e8f3ef7/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/952e065757a043e780625a3b2b1760df/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/982c2b76149c48a58f40936146e4a99d/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/9b174f057ad94700b8a171eb945c85b3/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/9fea58419006475d87856e12344f7f5c/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/a4358223aa17497dbce2dba001771002/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/a6ae97c8848942fe8ac6e1dafb8f875b/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/a6ffe739d9164b8682aa9987798541af/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/a9a5b5121e624e0693d04aa03a4066ea/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/a9e8aec3585f4dc8b8b4efbbd44cec77/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/af551b1281404e69becdc8d76e794640/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/b010b5910da94933bac48eaeaf6e28a9/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/b1e642bf1dde4cb09ff2f1e891689149/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/b2b4be04af764c4984605cf53a4aa7a2/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/b3b52108c0f44c30a88da4c8b4009d02/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/b6628ec84bca4a5f8b626edf888d343c/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/b91c8ec9af3e43cdb8004502eaf08ff9/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/ba1b67c942ac4591a0d8006dd53fb0a3/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/ba96997178964a079e5e017e746a0978/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/bc2b4edf031e45988fb3bc58f3bd6062/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/bd6366a5dd144f2085a11e957ff3b7d5/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/bf117972b60546dfb4be013ae32b7291/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/c2cfbd1b01274b23b6a806eee4bb9929/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/c37349eb12c94871a7cb373a2f742f59/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/c431cabf9f034747be6d7c6a4e343f1f/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/c70810433b3d4a0aab7de72847abd261/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/cbcc6e72002f4a4094f0c388ae463a68/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/cfaae46b8ab14946be124a131072464f/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/d62ae97b09484784b7208caf8e4c1de6/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/d6921d267eae4740bd2482e5d3dbf331/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/d6dedd216acc4316b6e12abf561b3412/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/d84d39db3d8d4990bc6cb65aaa7bd032/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/d898011227f14b6588f29e3331caff5f/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/db6dfbd184d049efb274e1b1bff46f2b/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/dbc51e0bbea249ed9056ef6a42eec690/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/de2192a643de419d976e7c84fafeef73/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/e1099b4512c744358036e0895f068ee0/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/e54b7529b4564aa1814d27b6304dc1be/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/e63b9605643a4c1aa278c637da39c4aa/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/ec4571c3de3c4c7d88e4a9b403bf5008/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/ed5aec9b35ae4daca831542a97ab9645/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/eda7db05b7854e20810b1d060f3bd214/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/f3942666b7e24809a62b5934e9885a4e/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/f743315f1b134b8a94b74c57d329cc38/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/f7526c103e924568bdc8d03473b711d3/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/f7b67d78cca14302aeb34091d2bb3f26/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/f83e8061b95b4078bcad43bd3307acfb/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/f8e76d8f03734c02b6e9d3d4a277fca9/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/fb53704f803e46a7b52924c65da275dc/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `docs/NEXT_STEPS.md` | docs | non_production | review_for_archive | archive | - |
| `docs/PROJECT_STATUS.md` | docs | non_production | review_for_archive | archive | - |

## Production-Critical Files

| Path | Primary Role | Criticality | Cleanup | Flags | Risk Notes |
| --- | --- | --- | --- | --- | --- |
| `src/universal_visual_os_agent/config/__init__.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/config/models.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/config/modes.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/geometry/__init__.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/geometry/interfaces.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/geometry/models.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/geometry/transforms.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/integrations/windows/__init__.py` | runtime | critical | keep | - | high_internal_import_count:11, facade_reexport_surface |
| `src/universal_visual_os_agent/integrations/windows/capture.py` | runtime | critical | review_for_split | - | oversized_module, high_internal_import_count:8 |
| `src/universal_visual_os_agent/integrations/windows/capture_backends.py` | runtime | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/capture_desktop_duplication.py` | runtime | critical | keep | - | - |
| `src/universal_visual_os_agent/integrations/windows/capture_dxcam.py` | runtime | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/capture_models.py` | runtime | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/click.py` | runtime | critical | keep | - | - |
| `src/universal_visual_os_agent/integrations/windows/screen_metrics.py` | runtime | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/perception/__init__.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/perception/interfaces.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/perception/models.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/semantics/__init__.py` | semantics | critical | keep | - | high_internal_import_count:15, facade_reexport_surface |
| `src/universal_visual_os_agent/semantics/building.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/candidate_exposure.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/candidate_generation.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/candidate_scoring.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/interfaces.py` | semantics | critical | review_for_cycle_isolation | - | cycle_member, high_internal_import_count:11 |
| `src/universal_visual_os_agent/semantics/layout.py` | semantics | critical | keep | - | - |
| `src/universal_visual_os_agent/semantics/layout_region_analysis.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/models.py` | semantics | critical | keep | - | high_internal_import_count:14 |
| `src/universal_visual_os_agent/semantics/ocr.py` | semantics | critical | review_for_cycle_isolation | - | cycle_member, oversized_module |
| `src/universal_visual_os_agent/semantics/ocr_enrichment.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/ocr_rapidocr.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/ontology.py` | semantics | critical | keep | - | - |
| `src/universal_visual_os_agent/semantics/preparation.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/semantic_delta.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/semantic_layout_enrichment.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/state.py` | semantics | critical | review_for_split | - | oversized_module |

## Full Inventory

| Path | Primary Role | Criticality | Cleanup | Flags | Risk Notes |
| --- | --- | --- | --- | --- | --- |
| `.github/workflows/ci.yml` | support | non_production | keep | - | - |
| `.gitignore` | support | non_production | keep | - | - |
| `.tmp_test_artifacts/0089eed4a00f4f4e90225eadbec04665/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/047ac50140014bee8c64506c3020430a/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/0789d2025f244764bd4e3031309fba08/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/079b72f236224b08a52077f68c832f31/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/0d7be4de55a247cda0398d84320b0be0/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/0d88702574ec4174a30676bf8b1598d6/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/0e20dfc6fac248e7983e133ad4b72f32/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/10c3ae108d3d4238902b56eaca3c0ea5/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/1187b27d80b445d59cfed00297eb3d24/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/1201655668ca49dc9ad2c5edef14bd4d/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/1218f54081ad492a9579a876ec6fe10c/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/1496161461a047f680c8c84a6f6dcdc4/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/14ee3048239f4df59da5d0af2d5331c4/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/1cbe4b2cef0842809ed553d348ef921d/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/1fb9a8bafa6d4c499df31509c55db25d/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/21006d80acd440a1bf5dc27711cc69f1/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/2128506b72c34098bd28ed456ccd64e4/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/216c96a61eda45259a97d3d44478c219/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/26bf76693fb540c88a863fe56efc9d38/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/27f4e5c243654ff7a6743a4ce71d7afa/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/2852fa5876794fb1b1445927875a5487/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/2998d397034c4b27aeca319b2fb40b66/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/2d8028e7ac214a9bacc9732e905e8113/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/318c623f0fbe42908bb5731e6aaa1426/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/353a02087c804c7a9d62924890d26a82/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/375b8e04e06b4bad9f8ece63b2503b87/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/3b840c4b34944e77a10df665071bfed1/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/3cc6bed165b94c39b1aa7c2c51adde83/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/3ceb28537a8247ec946be68f46911f6f/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/3d5b44c7eb584b23b490097e36df1380/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/3f2da13e45394126892bdcd4ceda17a8/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/420ac1d92c8c4449a88b033a37e595ad/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/49778acd788940b3bb4a5b5224369891/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/4a62183db98f437ebe79c3fbd992ebc0/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/4f896fff0d39447380c78a7f53954142/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/4ff50a16ca0f48bf8f1687b3beec0c04/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/50073916e4294117b8c13be18ea6095b/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/52e67399c26c4e10a059880882d8437e/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/56557fe49fdb495091631709e1862862/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/5bc4ff6ffafa42b2976e2817701b1656/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/5d9c0aacf5f545c58a461900d5f83c84/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/5f55d0045be74b1195797482b3e0d337/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/605e33abfb36499d8fc04a782685939c/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/6116eb70770b42dd927c826b9d6dd47e/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/6278de17782e4f4c917ff3abf94581b9/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/633dae1d99f34f7e9d05dd0a6aff922e/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/6480a83a30044622ac84f3938bc3142e/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/66c407f5109b45e69649975555dbbed8/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/684e76c264344459ae1a65aaada283a2/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/696e525e58a8431e99028570e01bc548/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/69d3723a04484457a0685d935cabad58/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/6cb1e6d6dbb44486b15a1ed6a12886f5/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/7016729db8ca42448994eab129ca6a1a/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/71fd8e15a0a045ce995625334db3bb77/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/73957570a910427885f40bb7917975ea/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/73f3d4202e6b49d596092cf0fe34e8d1/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/7400b80e47e44d1fb6ebaf6eac3b72a9/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/742df26d3e11487fb1b07a7e86fdba41/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/754b9946442d4eef9a9086ff501dedbb/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/7945d243fd3d49e1bc972ad306bbe1b1/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/79d8010e25e541bd92eb806580e494e9/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/82a1c46645314128b9ecf1951932b3bb/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/83893ba038a546799336d63bf7916ebf/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/86c3c0dabec5401c89158a8671d558ba/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/8d489f88d2d04b5fa42edce4941ebd61/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/8f2cc5875a52476b85bddbb1c4e482bd/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/901098bf301646bb8182dc188e8f3ef7/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/952e065757a043e780625a3b2b1760df/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/982c2b76149c48a58f40936146e4a99d/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/9b174f057ad94700b8a171eb945c85b3/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/9fea58419006475d87856e12344f7f5c/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/a4358223aa17497dbce2dba001771002/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/a6ae97c8848942fe8ac6e1dafb8f875b/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/a6ffe739d9164b8682aa9987798541af/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/a9a5b5121e624e0693d04aa03a4066ea/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/a9e8aec3585f4dc8b8b4efbbd44cec77/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/af551b1281404e69becdc8d76e794640/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/b010b5910da94933bac48eaeaf6e28a9/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/b1e642bf1dde4cb09ff2f1e891689149/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/b2b4be04af764c4984605cf53a4aa7a2/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/b3b52108c0f44c30a88da4c8b4009d02/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/b6628ec84bca4a5f8b626edf888d343c/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/b91c8ec9af3e43cdb8004502eaf08ff9/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/ba1b67c942ac4591a0d8006dd53fb0a3/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/ba96997178964a079e5e017e746a0978/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/bc2b4edf031e45988fb3bc58f3bd6062/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/bd6366a5dd144f2085a11e957ff3b7d5/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/bf117972b60546dfb4be013ae32b7291/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/c2cfbd1b01274b23b6a806eee4bb9929/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/c37349eb12c94871a7cb373a2f742f59/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/c431cabf9f034747be6d7c6a4e343f1f/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/c70810433b3d4a0aab7de72847abd261/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/cbcc6e72002f4a4094f0c388ae463a68/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/cfaae46b8ab14946be124a131072464f/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/d62ae97b09484784b7208caf8e4c1de6/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/d6921d267eae4740bd2482e5d3dbf331/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/d6dedd216acc4316b6e12abf561b3412/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/d84d39db3d8d4990bc6cb65aaa7bd032/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/d898011227f14b6588f29e3331caff5f/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/db6dfbd184d049efb274e1b1bff46f2b/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/dbc51e0bbea249ed9056ef6a42eec690/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/de2192a643de419d976e7c84fafeef73/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/e1099b4512c744358036e0895f068ee0/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/e54b7529b4564aa1814d27b6304dc1be/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/e63b9605643a4c1aa278c637da39c4aa/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/ec4571c3de3c4c7d88e4a9b403bf5008/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/ed5aec9b35ae4daca831542a97ab9645/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/eda7db05b7854e20810b1d060f3bd214/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/f3942666b7e24809a62b5934e9885a4e/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/f743315f1b134b8a94b74c57d329cc38/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/f7526c103e924568bdc8d03473b711d3/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/f7b67d78cca14302aeb34091d2bb3f26/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/f83e8061b95b4078bcad43bd3307acfb/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/f8e76d8f03734c02b6e9d3d4a277fca9/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `.tmp_test_artifacts/fb53704f803e46a7b52924c65da275dc/agent.sqlite3` | support | non_production | review_for_archive | archive | - |
| `AGENTS.md` | support | non_production | keep | - | - |
| `README.md` | support | non_production | keep | - | - |
| `docs/NEXT_STEPS.md` | docs | non_production | review_for_archive | archive | - |
| `docs/PROJECT_STATUS.md` | docs | non_production | review_for_archive | archive | - |
| `docs/REPO_INVENTORY.json` | docs | non_production | keep | - | - |
| `docs/REPO_INVENTORY.md` | docs | non_production | keep | - | - |
| `docs/VALIDATION_REPORT_TEMPLATE.md` | docs | non_production | keep | - | - |
| `docs/execplan.md` | docs | non_production | keep | - | - |
| `docs/spec.md` | docs | non_production | keep | - | - |
| `pyproject.toml` | support | non_production | keep | - | - |
| `requirements.in` | support | non_production | keep | - | - |
| `requirements.txt` | support | non_production | keep | - | - |
| `src/universal_visual_os_agent/__init__.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/actions/__init__.py` | actions | supporting | keep | - | facade_reexport_surface |
| `src/universal_visual_os_agent/actions/dry_run.py` | actions | supporting | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/actions/interfaces.py` | actions | supporting | review_for_cycle_isolation | - | cycle_member, high_internal_import_count:9, high_cross_package_import_count:5 |
| `src/universal_visual_os_agent/actions/models.py` | actions | supporting | keep | - | - |
| `src/universal_visual_os_agent/actions/safe_click.py` | actions | supporting | review_for_cycle_isolation | - | cycle_member, oversized_module, high_cross_package_import_count:5 |
| `src/universal_visual_os_agent/actions/scaffolding.py` | actions | supporting | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/ai_architecture/__init__.py` | ai_contracts | supporting | keep | - | facade_reexport_surface |
| `src/universal_visual_os_agent/ai_architecture/arbitration.py` | ai_contracts | supporting | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/ai_architecture/contracts.py` | ai_contracts | supporting | review_for_split | - | oversized_module, high_cross_package_import_count:5 |
| `src/universal_visual_os_agent/ai_architecture/interfaces.py` | ai_contracts | supporting | keep | - | high_cross_package_import_count:4 |
| `src/universal_visual_os_agent/ai_architecture/ontology.py` | ai_contracts | supporting | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/ai_boundary/__init__.py` | ai_contracts | supporting | keep | - | - |
| `src/universal_visual_os_agent/ai_boundary/interfaces.py` | ai_contracts | supporting | keep | - | - |
| `src/universal_visual_os_agent/ai_boundary/models.py` | ai_contracts | supporting | review_for_split | - | oversized_module, high_cross_package_import_count:4 |
| `src/universal_visual_os_agent/ai_boundary/validation.py` | ai_contracts | supporting | review_for_split | - | oversized_module, high_cross_package_import_count:5 |
| `src/universal_visual_os_agent/app/__init__.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/app/interfaces.py` | core | supporting | keep | - | high_internal_import_count:8, high_cross_package_import_count:7 |
| `src/universal_visual_os_agent/app/logging.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/app/models.py` | core | supporting | keep | - | high_cross_package_import_count:7 |
| `src/universal_visual_os_agent/app/orchestration.py` | core | supporting | review_for_split | - | oversized_module, high_internal_import_count:10, high_cross_package_import_count:7 |
| `src/universal_visual_os_agent/audit/__init__.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/audit/interfaces.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/audit/models.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/config/__init__.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/config/models.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/config/modes.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/core/__init__.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/core/events.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/core/interfaces.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/geometry/__init__.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/geometry/interfaces.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/geometry/models.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/geometry/transforms.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/integrations/__init__.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/integrations/windows/__init__.py` | runtime | critical | keep | - | high_internal_import_count:11, facade_reexport_surface |
| `src/universal_visual_os_agent/integrations/windows/capture.py` | runtime | critical | review_for_split | - | oversized_module, high_internal_import_count:8 |
| `src/universal_visual_os_agent/integrations/windows/capture_backends.py` | runtime | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/capture_desktop_duplication.py` | runtime | critical | keep | - | - |
| `src/universal_visual_os_agent/integrations/windows/capture_dxcam.py` | runtime | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/capture_gdi.py` | diagnostic | non_production | retain_as_diagnostic_only | diagnostic | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/capture_models.py` | runtime | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/capture_printwindow.py` | diagnostic | non_production | retain_as_diagnostic_only | diagnostic | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/click.py` | runtime | critical | keep | - | - |
| `src/universal_visual_os_agent/integrations/windows/dxcam_capture_diagnostic.py` | diagnostic | non_production | retain_as_diagnostic_only | diagnostic | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/foreground_capture_diagnostic.py` | diagnostic | non_production | retain_as_diagnostic_only | diagnostic | oversized_module |
| `src/universal_visual_os_agent/integrations/windows/screen_metrics.py` | runtime | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/memory/__init__.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/perception/__init__.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/perception/interfaces.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/perception/models.py` | core | critical | keep | - | - |
| `src/universal_visual_os_agent/persistence/__init__.py` | core | supporting | keep | - | facade_reexport_surface |
| `src/universal_visual_os_agent/persistence/interfaces.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/persistence/models.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/persistence/schema.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/persistence/services.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/persistence/sqlite.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/planning/__init__.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/planning/interfaces.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/planning/models.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/policy/__init__.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/policy/engine.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/policy/interfaces.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/policy/models.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/recovery/__init__.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/recovery/interfaces.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/recovery/loading.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/recovery/models.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/replay/__init__.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/replay/harness.py` | core | supporting | keep | - | high_internal_import_count:8, high_cross_package_import_count:7 |
| `src/universal_visual_os_agent/replay/models.py` | core | supporting | keep | - | - |
| `src/universal_visual_os_agent/replay/synthetic.py` | core | supporting | keep | - | high_cross_package_import_count:5 |
| `src/universal_visual_os_agent/scenarios/__init__.py` | scenario | supporting | keep | - | facade_reexport_surface |
| `src/universal_visual_os_agent/scenarios/action_flow.py` | scenario | supporting | review_for_split | - | oversized_module, high_internal_import_count:13, high_cross_package_import_count:8 |
| `src/universal_visual_os_agent/scenarios/definition.py` | scenario | supporting | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/scenarios/interfaces.py` | scenario | supporting | keep | - | high_cross_package_import_count:5 |
| `src/universal_visual_os_agent/scenarios/loop.py` | scenario | supporting | review_for_split | - | oversized_module, high_internal_import_count:9, high_cross_package_import_count:4 |
| `src/universal_visual_os_agent/scenarios/models.py` | scenario | supporting | review_for_split | - | oversized_module, high_internal_import_count:8, high_cross_package_import_count:4 |
| `src/universal_visual_os_agent/scenarios/state_machine.py` | scenario | supporting | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/__init__.py` | semantics | critical | keep | - | high_internal_import_count:15, facade_reexport_surface |
| `src/universal_visual_os_agent/semantics/building.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/candidate_exposure.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/candidate_generation.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/candidate_scoring.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/interfaces.py` | semantics | critical | review_for_cycle_isolation | - | cycle_member, high_internal_import_count:11 |
| `src/universal_visual_os_agent/semantics/layout.py` | semantics | critical | keep | - | - |
| `src/universal_visual_os_agent/semantics/layout_region_analysis.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/models.py` | semantics | critical | keep | - | high_internal_import_count:14 |
| `src/universal_visual_os_agent/semantics/ocr.py` | semantics | critical | review_for_cycle_isolation | - | cycle_member, oversized_module |
| `src/universal_visual_os_agent/semantics/ocr_enrichment.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/ocr_rapidocr.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/ontology.py` | semantics | critical | keep | - | - |
| `src/universal_visual_os_agent/semantics/preparation.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/semantic_delta.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/semantic_layout_enrichment.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/semantics/state.py` | semantics | critical | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/testing/__init__.py` | support | supporting | keep | - | - |
| `src/universal_visual_os_agent/testing/fixtures.py` | support | supporting | keep | - | high_cross_package_import_count:4 |
| `src/universal_visual_os_agent/testing/repo_inventory.py` | support | supporting | review_for_split | - | oversized_module |
| `src/universal_visual_os_agent/testing/validation.py` | support | supporting | keep | - | - |
| `src/universal_visual_os_agent/verification/__init__.py` | core | supporting | keep | - | facade_reexport_surface |
| `src/universal_visual_os_agent/verification/explanations.py` | core | supporting | review_for_cycle_isolation | - | cycle_member, oversized_module |
| `src/universal_visual_os_agent/verification/goal_oriented.py` | core | supporting | review_for_cycle_isolation | - | cycle_member, oversized_module |
| `src/universal_visual_os_agent/verification/interfaces.py` | core | supporting | review_for_cycle_isolation | - | cycle_member |
| `src/universal_visual_os_agent/verification/models.py` | core | supporting | review_for_cycle_isolation | - | cycle_member |
| `tests/conftest.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_action_intent_scaffolding.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_ai_architecture_scaffolding.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_ai_boundary_contracts.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_candidate_ontology.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_config_models.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_dry_run_action_engine.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_geometry_transforms.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_goal_oriented_verification.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_main_loop_skeleton.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_mode_selection.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_persistence_recovery.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_policy_safety.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_rapidocr_text_extraction_backend.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_repo_inventory.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_safe_click_prototype.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_scenario_action_flow.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_scenario_definition.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_scenario_loop.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_scenario_state_machine.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_semantic_candidate_exposure.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_semantic_candidate_generation.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_semantic_candidate_scoring.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_semantic_delta.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_semantic_extraction_adapter.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_semantic_layout_enrichment.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_semantic_layout_region_analysis.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_semantic_ocr_enrichment.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_semantic_state_builder.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_semantic_state_pipeline.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_semantic_text_extraction_adapter.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_validation_replay_harness.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_verification_explanations.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_windows_capture_provider.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_windows_capture_runtime_architecture.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_windows_desktop_duplication_backend.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_windows_dxcam_capture_backend.py` | test_only | non_production | retain_as_test_only | - | - |
| `tests/test_windows_dxcam_capture_diagnostic.py` | test_only | non_production | retain_as_test_only | diagnostic | - |
| `tests/test_windows_foreground_capture_diagnostic.py` | test_only | non_production | retain_as_test_only | diagnostic | - |
| `tests/test_windows_screen_metrics_provider.py` | test_only | non_production | retain_as_test_only | - | - |