#version 440
#extension GL_GOOGLE_include_directive : enable
#include "deep-blue-field.glsl"
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float time;
    float flow;
    float energy;
    vec3 ripple0;
    vec3 ripple1;
    vec3 ripple2;
    vec3 ripple3;
};
layout(binding = 1) uniform sampler2D source;
layout(binding = 2) uniform sampler2D caustics;
layout(binding = 3) uniform sampler2D normals;

void main() {
    vec2 uv = qt_TexCoord0;
    vec4 body = texture(source, uv);
    if (body.a < 0.001) { fragColor = vec4(0); return; }
    vec3 n = normalize(texture(normals, uv).rgb * 2.0 - 1.0);
    float waves = deepWave(ripple0, uv, vec2(1)) + deepWave(ripple1, uv, vec2(1))
        + deepWave(ripple2, uv, vec2(1)) + deepWave(ripple3, uv, vec2(1));
    vec2 projected = uv * 0.88 + n.xy * 0.10 + vec2(flow * 0.018, -flow * 0.011);
    projected += vec2(sin(uv.y * 17.0 - time), cos(uv.x * 15.0 + time)) * waves * 0.012;
    float caustic = deepCaustic(caustics, projected, flow);
    float secondary = deepCaustic(caustics, projected * 1.6 + vec2(0.37, 0.13), flow + 2.0);
    float relief = dot(body.rgb / body.a, vec3(0.3, 0.5, 0.2));
    float facing = max(0.0, dot(n, normalize(vec3(-0.35, -0.6, 0.72))));
    float rim = pow(1.0 - max(0.0, n.z), 2.5);
    vec3 shallow = vec3(0.025, 0.26, 0.39);
    vec3 abyss = vec3(0.008, 0.048, 0.17);
    vec3 color = mix(shallow, abyss, smoothstep(0.05, 1.0, uv.y)) * (0.55 + facing * 0.65 + relief * 0.28);
    color += vec3(0.18, 0.78, 0.98) * (caustic * (0.70 + energy * 0.48) * (0.35 + facing * 0.65)
        + secondary * 0.13 + rim * (0.28 + energy * 0.18) + max(0.0, waves) * 0.28);
    float shine = pow(max(0.0, dot(n, normalize(vec3(-0.30, -0.38, 1.0)))), 38.0);
    color += vec3(0.58, 0.9, 0.96) * shine * (0.11 + caustic * 0.22);
    float alpha = body.a * 0.96;
    fragColor = vec4(clamp(color, 0.0, 1.0) * alpha, alpha) * qt_Opacity;
}
