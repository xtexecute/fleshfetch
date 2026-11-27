#version 440
#extension GL_GOOGLE_include_directive : enable
#include "sunlight-field.glsl"
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 aim;
    float aspect;
    float flash;
    float sweep;
    vec2 artOrigin;
    vec2 artSize;
    vec2 scaleFactors;
    float angle;
    float sunbreak;
    float charge;
};
layout(binding = 1) uniform sampler2D source;

float silhouette(vec2 uv, vec2 spread) {
    return max(max(texture(source, uv + vec2(spread.x, 0.0)).a,
                   texture(source, uv - vec2(spread.x, 0.0)).a),
               max(texture(source, uv + vec2(0.0, spread.y)).a,
                   texture(source, uv - vec2(0.0, spread.y)).a));
}

void main() {
    vec4 texel = texture(source, qt_TexCoord0);
    vec2 ratio = vec2(1.0, aspect);
    float halo = 0.0;
    if (sunbreak > 0.001 || charge > 0.001) {
        vec2 stepSize = vec2(0.024, 0.024) / (ratio * max(artSize, vec2(0.01)));
        float edge = 0.70 * silhouette(qt_TexCoord0, stepSize * 0.40)
                   + 0.30 * silhouette(qt_TexCoord0, stepSize);
        halo = edge * clamp(0.83 * sunbreak + 0.16 * charge, 0.0, 0.86);
    }
    vec3 rim = vec3(1.0, 0.91, 0.55);
    if (texel.a <= 0.001) {
        fragColor = vec4(rim * halo, halo) * qt_Opacity;
        return;
    }
    vec2 point = (artOrigin + qt_TexCoord0 * artSize - 0.5) * ratio * scaleFactors;
    float c = cos(angle), s = sin(angle);
    vec2 uv = mat2(c, s, -s, c) * point / ratio + 0.5;
    float field = sunField(uv, aim, aspect, flash, sweep);
    vec3 rgb = texel.rgb / texel.a;
    float value = dot(rgb, vec3(0.25, 0.61, 0.14));
    float lift = clamp(field * (0.49 + 0.38 * value) + sunbreak * (0.23 + 0.31 * value), 0.0, 0.83);
    vec3 lit = rgb + (1.0 - rgb) * vec3(1.0, 0.79, 0.32) * lift;
    fragColor = (vec4(lit * texel.a, texel.a) + vec4(rim * halo, halo) * (1.0 - texel.a)) * qt_Opacity;
}
