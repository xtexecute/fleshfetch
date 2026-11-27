#version 440
#extension GL_GOOGLE_include_directive : enable
#include "deep-blue-field.glsl"
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 viewport;
    float time;
    float flow;
    float energy;
    float fill;
    vec3 wake0;
    vec3 wake1;
    vec3 wake2;
    vec3 wake3;
};
layout(binding = 1) uniform sampler2D caustics;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

void main() {
    vec2 uv = qt_TexCoord0;
    vec2 p = floor(uv * viewport) + 0.5;
    vec2 aspect = viewport / max(1.0, min(viewport.x, viewport.y));
    float wake = deepWave(wake0, uv, aspect) + deepWave(wake1, uv, aspect)
        + deepWave(wake2, uv, aspect) + deepWave(wake3, uv, aspect);
    float light = 0.0;
    for (int i = 0; i < 4; ++i) {
        float beam = float(i);
        float origin = 0.08 + beam * 0.25 + 0.025 * sin(time * 0.3 + beam * 2.0);
        float x = uv.x - origin - uv.y * (0.12 + 0.06 * sin(beam * 3.0));
        float width = 0.017 + uv.y * 0.045;
        float ray = exp(-x * x / (width * width));
        float shimmer = deepCaustic(caustics, vec2(origin * 1.8 + uv.y * 0.03, flow * 0.021), flow);
        light += ray * (0.11 + shimmer * 0.35) * exp(-uv.y * 2.3);
    }
    vec3 color = mix(vec3(0.022, 0.12, 0.18), vec3(0.009, 0.028, 0.085), uv.y);
    color += vec3(0.13, 0.52, 0.67) * light * (0.8 + energy * 0.45);
    color += vec3(0.04, 0.25, 0.38) * max(0.0, wake) * 0.30;
    vec2 currents = p + vec2(sin(p.y * 0.018 + time * 0.42) * 6.0, flow * 5.0);
    vec2 cell = floor(currents / 11.0), local = fract(currents / 11.0);
    float seed = hash(cell);
    float plankton = step(0.977, seed) * step(0.42, local.x) * step(local.x, 0.51)
        * step(0.42, local.y) * step(local.y, 0.51);
    color += vec3(0.14, 0.64, 0.72) * plankton * (0.22 + 0.18 * sin(time + seed * 24.0) + energy * 0.38);
    float top = viewport.y * (1.0 - 0.84 * clamp(fill / 100.0, 0.0, 1.0));
    float depth = p.y - top - 1.4 * sin(p.x * 0.043 + time) - sin(p.x * 0.085 - flow * 2.0);
    float pool = smoothstep(-0.5, 0.5, depth) * step(0.001, fill);
    float caustic = deepCaustic(caustics, vec2(p.x * 0.005, depth * 0.008) + vec2(0, -flow * 0.012), flow);
    vec3 tide = vec3(0.013, 0.075, 0.20) + vec3(0.06, 0.40, 0.58) * caustic * (0.12 + energy * 0.12);
    tide += vec3(0.12, 0.65, 0.79) * exp(-max(0.0, depth) / 1.6) * (0.42 + energy * 0.33);
    color = mix(color, tide, pool * 0.92);
    fragColor = vec4(color * 0.90, 0.90) * qt_Opacity;
}
