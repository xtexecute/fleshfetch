float panePulse(vec3 stroke, vec2 cell) {
    if (stroke.z >= 1.0)
        return 0.0;
    vec2 origin = texture(panes, stroke.xy).rg;
    float localTime = stroke.z - 0.74 * distance(origin, cell);
    return smoothstep(-0.018, 0.035, localTime) * (1.0 - smoothstep(0.076, 0.42, localTime));
}

float paneLight(vec2 cell) {
    return min(1.45, panePulse(pulse0, cell) + panePulse(pulse1, cell) + panePulse(pulse2, cell));
}
