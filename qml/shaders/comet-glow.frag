#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float strength;
    float outline;
    float texelX;
    float texelY;
};
layout(binding = 1) uniform sampler2D source;

void main() {
    vec2 uv = qt_TexCoord0;
    vec2 pixel = vec2(texelX, texelY);
    float center = texture(source, uv).a;
    float nearHalo = 0.0;
    float midHalo = 0.0;
    float farHalo = 0.0;
    for (int radius = 1; radius <= 3; ++radius) {
        vec2 d = pixel * float(radius * 5);
        float ring = 0.0;
        ring = max(ring, texture(source, uv + vec2(d.x, 0.0)).a);
        ring = max(ring, texture(source, uv - vec2(d.x, 0.0)).a);
        ring = max(ring, texture(source, uv + vec2(0.0, d.y)).a);
        ring = max(ring, texture(source, uv - vec2(0.0, d.y)).a);
        ring = max(ring, texture(source, uv + d).a);
        ring = max(ring, texture(source, uv - d).a);
        ring = max(ring, texture(source, uv + vec2(d.x, -d.y)).a);
        ring = max(ring, texture(source, uv + vec2(-d.x, d.y)).a);
        if (radius == 1) nearHalo = ring;
        else if (radius == 2) midHalo = ring;
        else farHalo = ring;
    }
    vec2 edge = pixel * 2.0;
    float rim = max(texture(source, uv + vec2(edge.x, 0.0)).a,
                    texture(source, uv - vec2(edge.x, 0.0)).a);
    rim = max(rim, texture(source, uv + vec2(0.0, edge.y)).a);
    rim = max(rim, texture(source, uv - vec2(0.0, edge.y)).a);
    float alpha = clamp(((nearHalo * 0.15 + midHalo * 0.18 + farHalo * 0.11) * strength
                         + rim * 0.52 * outline) * (1.0 - center), 0.0, 0.88);
    vec3 tint = mix(vec3(0.43, 0.27, 0.75), vec3(0.89, 0.82, 1.0),
                    clamp(outline * 0.9, 0.0, 1.0));
    fragColor = vec4(tint * alpha, alpha) * qt_Opacity;
}
