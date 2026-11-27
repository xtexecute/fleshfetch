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
    float sunbreak;
    float breakAge;
    vec2 breakCenter;
};

void main() {
    float field = sunField(qt_TexCoord0, aim, aspect, flash, sweep);
    float alpha = clamp(field * 0.48, 0.0, 0.62);
    vec3 tint = mix(vec3(1.0, 0.77, 0.41), vec3(1.0, 0.92, 0.67),
                    clamp(field * 0.54, 0.0, 1.0));
    vec4 shafts = vec4(tint * alpha, alpha);
    if (sunbreak > 0.001) {
        vec2 fromFlash = (qt_TexCoord0 - breakCenter) * vec2(1.0, aspect);
        float radius = length(fromFlash);
        float angle = atan(fromFlash.y, fromFlash.x);
        float crown = cos(angle * 9.0 + 0.65 + 0.67 * sin(angle * 3.0))
                    + 0.22 * cos(angle * 15.0 - 1.0);
        float ray = smoothstep(0.61, 0.99, crown);
        float reach = 0.49 + breakAge * 0.66;
        float flare = sunbreak * (0.23 + ray * 0.77) * (1.0 - smoothstep(0.14, reach, radius));
        float wave = sunbreak * (0.11 + ray * 0.16)
                   * softBand(radius, 0.13 + breakAge * 0.63, 0.007, 0.041);
        float shine = clamp(flare + wave, 0.0, 0.82);
        vec3 gold = mix(vec3(1.0, 0.68, 0.29), vec3(1.0, 0.96, 0.78),
                        1.0 - smoothstep(0.04, 0.40, radius));
        shafts = vec4(gold * shine, shine) + shafts * (1.0 - shine);
    }
    fragColor = shafts * qt_Opacity;
}
