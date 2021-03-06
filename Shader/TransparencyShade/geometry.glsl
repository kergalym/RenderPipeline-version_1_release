#version 410

#pragma include "Includes/Configuration.include"


// Unrolling speeds up this pass a lot on nvidia cards
#pragma optionNV (unroll all)

layout(triangles) in;
layout(triangle_strip, max_vertices = 120) out;

in vec2 texcoordVertex[3];
out vec2 texcoord;
flat out uint batchOffset;

uniform isampler2D pixelCountBuffer;


void main() {

    uint totalEntryCount = texelFetch(pixelCountBuffer, ivec2(0), 0).x;
    uint batchEntries = TRANSPARENCY_BATCH_SIZE * TRANSPARENCY_BATCH_SIZE;

    uint batchesToSpawn = uint(ceil(float(totalEntryCount) / float(batchEntries)));
    batchesToSpawn = min(batchesToSpawn, 40);

    for (uint batch = 0; batch < batchesToSpawn; batch++) {
        for (int i = 0; i < 3; i++) {
            gl_Position = gl_in[i].gl_Position;
            texcoord = texcoordVertex[i];
            batchOffset = batch * batchEntries;
            EmitVertex();
        }
        EndPrimitive();
    }
}