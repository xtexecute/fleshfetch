#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec3 lamp0;
    vec3 lamp1;
    vec3 lamp2;
    vec3 lamp3;
    vec3 lamp4;
    vec3 lamp5;
    vec3 lamp6;
    vec3 lamp7;
    vec2 bodyOrigin;
    vec2 bodySize;
    vec2 bodySquish;
    float bodyAngle;
};
layout(binding = 1) uniform sampler2D source;

float lightAt(vec2 at, vec3 fly) {
    vec2 d = at - fly.xy;
    return exp(-dot(d, d) / 170.0) * fly.z;
}

void main() {
    vec4 texel = texture(source, qt_TexCoord0);
    vec2 p = (qt_TexCoord0 - 0.5) * bodySize * bodySquish;
    float c = cos(bodyAngle), s = sin(bodyAngle);
    p = mat2(c, s, -s, c) * p + bodyOrigin + bodySize * 0.5;
    float light = lightAt(p, lamp0) + lightAt(p, lamp1) + lightAt(p, lamp2) + lightAt(p, lamp3)
                + lightAt(p, lamp4) + lightAt(p, lamp5) + lightAt(p, lamp6) + lightAt(p, lamp7);
    light = min(light, 2.0);
    vec3 color = texel.rgb * vec3(0.87, 0.89, 0.78);
    color += vec3(0.15, 0.12, 0.035) * light * texel.a;
    color += texel.rgb * vec3(0.075, 0.083, 0.027) * light;
    fragColor = vec4(min(color, vec3(texel.a)), texel.a) * qt_Opacity;
}
