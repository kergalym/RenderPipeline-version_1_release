#version 400

uniform mat4 p3d_ModelViewProjectionMatrix;

in vec4 p3d_Vertex;
out vec2 texcoordVertex;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    texcoordVertex =  sign(p3d_Vertex.xz * 0.5 + 0.5);
}