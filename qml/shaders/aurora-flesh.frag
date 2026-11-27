#version 440
#extension GL_GOOGLE_include_directive : enable
#include "aurora-field.glsl"
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 bodyOrigin;
    vec2 bodySize;
    vec2 center;
    float extent;
    float time;
    float flow;
    float energy;
    vec3 stroke0;
    vec3 stroke1;
    vec3 stroke2;
    vec3 stroke3;
};
layout(binding = 1) uniform sampler2D source;

void main() {
    vec2 uv = qt_TexCoord0;
    vec4 body = texture(source, uv);
    if (body.a < 0.001) { fragColor = vec4(0); return; }
    vec2 p = (uv * bodySize + bodyOrigin - center) / extent;
    vec4 light = auroraCurtain(p, time, flow, energy, 0.0, stroke0, stroke1, stroke2, stroke3);
    vec3 original = body.rgb / body.a;
    float luminance = dot(original, vec3(0.3, 0.5, 0.2));
    vec2 d = vec2(1.5) / max(vec2(1), bodySize);
    float edge = 1.0 - min(min(texture(source, uv + vec2(d.x, 0)).a, texture(source, uv - vec2(d.x, 0)).a),
        min(texture(source, uv + vec2(0, d.y)).a, texture(source, uv - vec2(0, d.y)).a));
    vec3 tint = auroraColor(0.2, 0.5 + 0.5 * sin(p.x * 10.0 + flow));
    float reflection = min(0.63, light.a * 0.43 + edge * (0.28 + energy * 0.31));
    vec3 color = mix(original * 0.82, tint * (0.30 + luminance * 0.8), reflection);
    color += light.rgb * (0.12 + luminance * 0.15);
    fragColor = vec4(clamp(color, 0.0, 1.0) * body.a, body.a) * qt_Opacity;
}
