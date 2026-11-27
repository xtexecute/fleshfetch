#version 440
#extension GL_GOOGLE_include_directive : enable
#include "sundial-light.glsl"

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float sunAngle;
};
layout(binding = 1) uniform sampler2D source;

void main() {
    vec4 texel = texture(source, qt_TexCoord0);
    float sun = sunVisibility(sunHeight(sunAngle));
    float lit = clamp(0.70 - 0.72 * dot(qt_TexCoord0 - 0.5,
                                         vec2(cos(sunAngle), 0.58)), 0.0, 1.0);
    vec3 ambient = mix(vec3(0.68, 0.76, 0.89), vec3(0.83, 0.79, 0.78), sun);
    vec3 daylight = sunColor(sunAngle) * sun * lit;
    vec3 litColor = texel.rgb * (ambient + daylight * 0.40) + daylight * texel.a * 0.014;
    fragColor = vec4(min(litColor, vec3(texel.a)), texel.a) * qt_Opacity;
}
