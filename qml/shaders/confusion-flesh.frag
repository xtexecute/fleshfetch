#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float phase;
};
layout(binding = 1) uniform sampler2D source;

void main() {
    float wave = 0.5 - 0.5 * cos(phase);
    vec2 uv = qt_TexCoord0;
    uv.x += (0.002 + 0.006 * wave) * sin(uv.y * 17.0 + phase)
          + 0.0015 * sin(uv.y * 34.0 - phase * 0.7);
    uv.y += 0.002 * wave * sin(uv.x * 19.0 - phase);
    if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
        fragColor = vec4(0.0);
        return;
    }
    vec4 flesh = texture(source, uv);
    vec3 purple = min(flesh.rgb * vec3(0.70, 0.48, 1.10)
                    + flesh.a * vec3(0.09, 0.02, 0.19), vec3(flesh.a));
    fragColor = vec4(mix(flesh.rgb, purple, wave * 0.72), flesh.a) * qt_Opacity;
}
