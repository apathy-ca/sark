-- MCP Security Plugin Schema

return {
  name = "mcp-security",
  fields = {
    {
      config = {
        type = "record",
        fields = {
          {
            opa_url = {
              type = "string",
              required = true,
              default = "http://opa:8181",
            },
          },
          {
            opa_timeout = {
              type = "number",
              required = false,
              default = 1000,
            },
          },
        },
      },
    },
  },
}
