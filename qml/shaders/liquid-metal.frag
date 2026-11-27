#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec3 ripple0;
    vec3 ripple1;
    vec3 ripple2;
};
layout(binding = 1) uniform sampler2D source;

void ripple(vec3 pulse, vec2 uv, inout vec2 shift, inout float reflection) {
    float t = pulse.z;
    if (t >= 1.0)
        return;
    vec2 fromHit = uv - pulse.xy;
    float d = length(fromHit);
    float crest = d - t * 0.77;
    float band = 1.0 - smoothstep(0.017, 0.105, abs(crest));
    float energy = band * smoothstep(0.0, 0.065, t) * (1.0 - t);
    float wave = sin(crest * 83.0);
    shift += fromHit / max(d, 0.012) * wave * energy * 0.045;
    reflection += cos(crest * 83.0 + 0.7) * energy * 0.24;
}

void main() {
    vec2 uv = qt_TexCoord0;
    vec4 base = texture(source, uv);
    if (base.a <= 0.001 || min(ripple0.z, min(ripple1.z, ripple2.z)) >= 1.0) {
        fragColor = base * qt_Opacity;
        return;
    }

    vec2 shift = vec2(0.0);
    float reflection = 0.0;
    ripple(ripple0, uv, shift, reflection);
    ripple(ripple1, uv, shift, reflection);
    ripple(ripple2, uv, shift, reflection);

    vec4 warped = texture(source, uv + clamp(shift, vec2(-0.065), vec2(0.065)));
    // The original alpha remains the hit mask, even where a wave reaches the edge.
    vec3 color = mix(base.rgb / base.a, warped.rgb / max(warped.a, 0.01),
                     smoothstep(0.02, 0.80, warped.a));
    color += vec3(0.85, 0.95, 1.0) * clamp(reflection, -0.26, 0.34);
    fragColor = vec4(clamp(color, 0.0, 1.0) * base.a, base.a) * qt_Opacity;
}
