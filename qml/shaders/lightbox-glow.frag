#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float exposure;
    vec2 size;
};

void main() {
    vec2 p = qt_TexCoord0 * size;
    vec2 d = abs(p - vec2(72.0, 72.0)) - vec2(45.0, 44.0);
    float distance = length(max(d, vec2(0.0)));
    float glow = exp(-distance * distance / (110.0 + exposure * 140.0));
    float alpha = glow * (0.10 + exposure * 0.22);
    fragColor = vec4(vec3(0.96, 0.86, 0.57) * alpha, alpha) * qt_Opacity;
}
