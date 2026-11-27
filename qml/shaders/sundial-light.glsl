float sunHeight(float angle) {
    return sin(angle);
}

float sunVisibility(float height) {
    return smoothstep(-0.15, 0.15, height);
}

vec3 sunColor(float angle) {
    float high = smoothstep(0.0, 0.92, sunHeight(angle));
    vec3 horizon = mix(vec3(1.0, 0.65, 0.34), vec3(1.0, 0.42, 0.24),
                       smoothstep(1.4, 3.04, angle));
    return mix(horizon, vec3(1.0, 0.92, 0.68), high);
}
