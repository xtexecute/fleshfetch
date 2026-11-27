#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float exposure;
    float scan;
    vec2 hit;
};
layout(binding = 1) uniform sampler2D source;

void main() {
    vec4 texel = texture(source, qt_TexCoord0);
    vec3 raw = texel.rgb / max(texel.a, 0.001);
    float fat = smoothstep(0.38, 0.92, dot(raw, vec3(0.22, 0.60, 0.18)));
    float density = dot(raw, vec3(0.22, 0.60, 0.18));
    float sweep = (1.0 - smoothstep(0.008, 0.11, abs(qt_TexCoord0.y - scan)))
                * step(scan, 0.99);
    float point = 1.0 - smoothstep(0.0, 0.72, distance(qt_TexCoord0, hit));
    float passed = 1.0 - smoothstep(scan - 0.035, scan + 0.035, qt_TexCoord0.y);
    float intensity = min(1.0, pow(exposure, 0.55) * (0.88 + point * 0.16)) * passed;
    // Derive the temporary film exposure from the photo, retaining every vein.
    float silver = pow(smoothstep(0.13, 0.97, density), 0.64);
    vec3 film = mix(vec3(0.025, 0.12, 0.15), vec3(0.87, 0.99, 0.91), silver);
    film += vec3(0.04, 0.09, 0.08) * fat;
    vec3 color = mix(raw, film, intensity);
    color += vec3(0.40, 0.52, 0.35) * sweep * exposure * 0.22;
    fragColor = vec4(clamp(color, 0.0, 1.0) * texel.a, texel.a) * qt_Opacity;
}
