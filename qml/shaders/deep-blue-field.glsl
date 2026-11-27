float deepCaustic(sampler2D atlas, vec2 uv, float flow) {
    float f = mod(flow * 8.0, 64.0);
    float a = floor(f), b = mod(a + 1.0, 64.0);
    vec2 q = clamp(fract(uv), vec2(0.5 / 128.0), vec2(127.5 / 128.0));
    vec2 cellA = vec2(mod(a, 8.0), floor(a / 8.0));
    vec2 cellB = vec2(mod(b, 8.0), floor(b / 8.0));
    return mix(texture(atlas, (cellA + q) / 8.0).r, texture(atlas, (cellB + q) / 8.0).r, fract(f));
}

float deepWave(vec3 pulse, vec2 uv, vec2 aspect) {
    if (pulse.z >= 1.0) return 0.0;
    float d = length((uv - pulse.xy) * aspect) - pulse.z * 1.15;
    return cos(d * 95.0) * exp(-d * d / 0.003) * pow(1.0 - pulse.z, 1.4) * smoothstep(0.0, 0.055, pulse.z);
}
