import common;

struct VertexInput
{
    float3 position     : POSITION;
    float3 normal       : NORMAL;
    float3 color        : COLOR;
    float2 uv           : UV;
}

struct VertexOutput
{
    float4 location     : SV_Position;
    float3 position     : POSITION;
    float3 normal       : NORMAL;
    float3 color        : COLOR;
}

struct FragmentOutput
{
    float4 position     : SV_Target0;
    float4 albedo       : SV_Target1;
    float4 normal       : SV_Target2;
}

ConstantBuffer<UniformBuffer> ubo;

[shader("vertex")]
VertexOutput vertex_main(VertexInput input)
{
    VertexOutput output;

    float4 worldPos = mul(ubo.model, float4(input.position, 1.f));
    float4 viewPos = mul(ubo.view, worldPos);
    output.location = mul(ubo.projection, viewPos);
    output.position = viewPos.xyz;

    float3 worldNormal = normalize(mul((float3x3)ubo.model, input.normal));
    float3 viewNormal = normalize(mul((float3x3)ubo.view, worldNormal));

    output.normal = viewNormal;
    output.color = abs(viewNormal);
    return output;
}

[shader("fragment")]
FragmentOutput fragment_main(VertexOutput input)
{
    FragmentOutput output;
    output.position = float4(input.position, 1.f);
    output.albedo = float4(1.f);
    output.normal = float4(input.normal, 1.f);
    return output;
}