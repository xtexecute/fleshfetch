float softBand(float x, float center, float core, float feather) {
    return 1.0 - smoothstep(core, core + feather, abs(x - center));
}

float sunField(vec2 uv, vec2 aim, float aspect, float flash, float sweep) {
    vec2 ratio = vec2(1.0, aspect);
    vec2 origin = vec2(-0.14, -0.085 * aspect);
    vec2 light = aim * ratio - origin;
    vec2 axis = normalize(light);
    vec2 delta = uv * ratio - origin;
    float forward = dot(delta, axis);
    float across = dot(delta, vec2(-axis.y, axis.x)) / max(0.18, 0.22 + forward);
    float bands = 0.51 * softBand(across, -0.17, 0.031, 0.052)
                + 0.89 * softBand(across, 0.00, 0.055, 0.061)
                + 0.62 * softBand(across, 0.18, 0.027, 0.053)
                + 0.22 * softBand(across, 0.29, 0.011, 0.035);
    float reach = forward / length(light);
    float envelope = smoothstep(-0.1, 0.23, reach)
                   * (1.0 - 0.62 * smoothstep(0.92, 2.0, reach));
    float passing = softBand(reach, 0.35 + 1.38 * sweep, 0.033, 0.22);
    return bands * envelope * (0.57 + flash * (0.46 + 0.55 * passing));
}
