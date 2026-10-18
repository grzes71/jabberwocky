# 3D Graphics

Router for real-time 3D on the Atari 8-bit: fixed-point math without
multiply or divide, rotation and projection, polygon rasterization and fill
strategies, flat/Gouraud shading and texture mapping, GTIA luminance display
modes, double buffering, culling, and engine architecture.

Read `overview.md` first (the pipeline, the memory-for-cycles idea, and a
decision guide), then open only the focused file that matches the task.

- [overview.md](3d-graphics/overview.md) - Pipeline, central idea, decision guide
- [math.md](3d-graphics/math.md) - Fixed-point, quarter-square multiply, divide/reciprocal tables, sine folding, sqrt
- [rotation.md](3d-graphics/rotation.md) - Rotation (matrix / per-frame LUT / incremental), angle animation, mesh & normals
- [projection.md](3d-graphics/projection.md) - Perspective & 2.5D projection, near-plane clipping, normals
- [rasterizer.md](3d-graphics/rasterizer.md) - Edge walking, span buffer, five fill strategies, wireframe, dirty-box clear
- [shading.md](3d-graphics/shading.md) - Flat & Gouraud shading, N·L lighting, direct-shade vs dither
- [texturing.md](3d-graphics/texturing.md) - Affine & perspective-correct texture mapping, environment mapping
- [display.md](3d-graphics/display.md) - GTIA 9/10/11 modes, VSCROL square pixels, double buffering, main loop, bare-metal, scene scripts
- [culling-depth.md](3d-graphics/culling-depth.md) - Back-face culling, depth bucket sort
- [see-also.md](3d-graphics/see-also.md) - Cross-references
