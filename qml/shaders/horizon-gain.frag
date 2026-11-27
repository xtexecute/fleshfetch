#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float age;
    vec2 size;
    vec2 position;
    vec2 center;
    float radius;
    vec3 deformation;
};
layout(binding = 1) uniform sampler2D source;

void main() {
    vec4 glyph = texture(source, qt_TexCoord0);
    vec2 local = (qt_TexCoord0 - 0.5) * size;
    vec2 world = position + mat2(deformation.x, deformation.y,
                                 deformation.y, deformation.z) * local;
    float visible = smoothstep(radius - 0.45, radius + 0.55, distance(world, center));
    float shift = smoothstep(0.18, 0.98, age);
    vec3 redshift = mix(vec3(1.0), vec3(1.0, 0.55, 0.22), smoothstep(0.0, 0.45, shift));
    redshift = mix(redshift, vec3(0.91, 0.12, 0.08), smoothstep(0.32, 0.88, shift));
    redshift = mix(redshift, vec3(0.46, 0.025, 0.035), smoothstep(0.80, 1.0, shift));
    fragColor = vec4(glyph.rgb * redshift, glyph.a) * visible * qt_Opacity;
}
