#version 440
#extension GL_GOOGLE_include_directive : enable

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec3 pulse0;
    vec3 pulse1;
    vec3 pulse2;
    vec2 bodyOrigin;
    vec2 bodySize;
    vec2 bodySquish;
    float bodyAngle;
};
layout(binding = 1) uniform sampler2D glass;
layout(binding = 2) uniform sampler2D panes;
layout(binding = 3) uniform sampler2D routes;
#include "stained-glass-pulse.glsl"

vec4 floorLight() {
    vec2 uv = (qt_TexCoord0 - bodyOrigin - bodySize * vec2(0.10, 0.49))
            / max(vec2(0.001), bodySize * vec2(1.02, 0.77));
    uv.x -= (uv.y - 0.45) * 0.28;
    if (min(uv.x, uv.y) < 0.02 || max(uv.x, uv.y) > 0.98)
        return vec4(0.0);
    vec2 blur = vec2(0.029, 0.042);
    vec4 sampleColor = texture(glass, uv) * 0.30
                     + (texture(glass, uv + blur) + texture(glass, uv - blur)
                        + texture(glass, uv + vec2(-blur.x, blur.y))
                        + texture(glass, uv + vec2(blur.x, -blur.y))) * 0.175;
    vec2 cell = texture(panes, uv).rg;
    float light = paneLight(cell);
    float strength = (0.047 + light * 0.59) * (1.0 - 0.54 * smoothstep(0.32, 1.0, uv.y));
    vec3 color = min(sampleColor.rgb * (1.43 + 0.66 * light), vec3(sampleColor.a));
    return vec4(color, sampleColor.a) * strength;
}

vec4 shaft(vec3 route) {
    if (route.b == 0.0) return vec4(0.0);
    vec3 tint = texture(glass, route.rg).rgb;
    tint = min(vec3(1.0), tint * 1.54 + 0.085);
    vec2 cell = texture(panes, route.rg).rg;
    float strength = route.b * min(0.68, 0.15 + paneLight(cell) * 0.50);
    return vec4(tint, 1.0) * strength;
}

vec4 paneRays() {
    vec2 centered = (qt_TexCoord0 - 0.5) / max(bodySize, vec2(0.001));
    float c = cos(bodyAngle);
    float s = sin(bodyAngle);
    vec2 local = mat2(c, -s, s, c) * centered / max(bodySquish, vec2(0.01))
               + (vec2(0.5) - bodyOrigin) / max(bodySize, vec2(0.001));
    vec2 uv = (local + vec2(0.15, 0.0)) / vec2(1.3, 1.5);
    if (min(uv.x, uv.y) < 0.0 || max(uv.x, uv.y) >= 1.0)
        return vec4(0.0);
    // Two stacked masks store each shaft's source UV in RG and strength in B.
    uv.y *= 0.5;
    vec4 a = shaft(texture(routes, uv).rgb);
    vec4 b = shaft(texture(routes, uv + vec2(0.0, 0.5)).rgb);
    return a + b * (1.0 - a.a);
}

void main() {
    vec4 rays = paneRays();
    fragColor = (rays + floorLight() * (1.0 - rays.a)) * qt_Opacity;
}
