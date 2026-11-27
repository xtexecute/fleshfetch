#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float phase;
    float texelX;
    float texelY;
};
layout(binding = 1) uniform sampler2D source;

void main() {
    vec2 stepSize = vec2(texelX, texelY);
    vec2 uv = qt_TexCoord0;
    float halo = 0.0;
    for (int radius = 1; radius <= 3; ++radius) {
        vec2 offset = stepSize * float(radius * 5);
        halo += texture(source, uv + vec2(offset.x, 0.0)).a;
        halo += texture(source, uv - vec2(offset.x, 0.0)).a;
        halo += texture(source, uv + vec2(0.0, offset.y)).a;
        halo += texture(source, uv - vec2(0.0, offset.y)).a;
        halo += texture(source, uv + offset).a;
        halo += texture(source, uv - offset).a;
        halo += texture(source, uv + vec2(offset.x, -offset.y)).a;
        halo += texture(source, uv + vec2(-offset.x, offset.y)).a;
    }
    float pulse = 0.75 + 0.25 * (0.5 - 0.5 * cos(phase));
    float alpha = clamp(halo / 24.0 - texture(source, uv).a * 0.75, 0.0, 1.0)
                  * 0.55 * pulse;
    fragColor = vec4(vec3(0.55, 0.18, 0.95) * alpha, alpha) * qt_Opacity;
}
