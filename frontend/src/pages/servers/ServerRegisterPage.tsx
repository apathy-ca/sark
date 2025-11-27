import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { serversApi } from '@/services/api';
import { toast } from 'sonner';
import { useState } from 'react';

const serverSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255, 'Name too long'),
  description: z.string().optional(),
  transport: z.enum(['http', 'stdio', 'sse'], {
    required_error: 'Transport type is required',
  }),
  endpoint: z.string().url('Must be a valid URL').optional().or(z.literal('')),
  command: z.string().optional(),
  args: z.array(z.string()).optional(),
  env: z.record(z.string()).optional(),
  sensitivity_level: z.enum(['low', 'medium', 'high', 'critical']),
  tools: z.array(
    z.object({
      name: z.string().min(1, 'Tool name is required'),
      description: z.string().optional(),
      sensitivity_level: z.enum(['low', 'medium', 'high', 'critical']),
      input_schema: z.string().optional(),
    })
  ).optional(),
  metadata: z.record(z.string()).optional(),
});

type ServerFormData = z.infer<typeof serverSchema>;

export default function ServerRegisterPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(1);

  const {
    register,
    handleSubmit,
    watch,
    control,
    formState: { errors, isSubmitting },
  } = useForm<ServerFormData>({
    resolver: zodResolver(serverSchema),
    defaultValues: {
      transport: 'http',
      sensitivity_level: 'low',
      tools: [],
      metadata: {},
    },
  });

  const { fields: toolFields, append: appendTool, remove: removeTool } = useFieldArray({
    control,
    name: 'tools',
  });

  const transport = watch('transport');

  const mutation = useMutation({
    mutationFn: serversApi.create,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['servers'] });
      toast.success('Server registered successfully');
      navigate(`/servers/${data.id}`);
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to register server');
    },
  });

  const onSubmit = (data: ServerFormData) => {
    // Clean up data based on transport type
    const payload: any = {
      name: data.name,
      description: data.description,
      transport: data.transport,
      sensitivity_level: data.sensitivity_level,
      tools: data.tools,
      metadata: data.metadata,
    };

    if (data.transport === 'http' || data.transport === 'sse') {
      payload.endpoint = data.endpoint;
    } else if (data.transport === 'stdio') {
      payload.command = data.command;
      payload.args = data.args;
      payload.env = data.env;
    }

    mutation.mutate(payload);
  };

  const renderStepIndicator = () => (
    <div className="flex items-center justify-center mb-8">
      {[1, 2, 3].map((stepNum) => (
        <div key={stepNum} className="flex items-center">
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold ${
              step >= stepNum
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground'
            }`}
          >
            {stepNum}
          </div>
          {stepNum < 3 && (
            <div
              className={`w-20 h-1 mx-2 ${
                step > stepNum ? 'bg-primary' : 'bg-muted'
              }`}
            />
          )}
        </div>
      ))}
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Register MCP Server</h1>
        <button
          onClick={() => navigate('/servers')}
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          ← Back to Servers
        </button>
      </div>

      {renderStepIndicator()}

      <form onSubmit={handleSubmit(onSubmit)} className="bg-card p-6 rounded-lg border">
        {/* Step 1: Basic Information */}
        {step === 1 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold mb-4">Basic Information</h2>

            <div>
              <label className="block text-sm font-medium mb-2">
                Server Name <span className="text-red-500">*</span>
              </label>
              <input
                {...register('name')}
                className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="My MCP Server"
              />
              {errors.name && (
                <p className="text-red-500 text-sm mt-1">{errors.name.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Description</label>
              <textarea
                {...register('description')}
                className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                rows={3}
                placeholder="Describe what this server does..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Transport Type <span className="text-red-500">*</span>
              </label>
              <select
                {...register('transport')}
                className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="http">HTTP</option>
                <option value="stdio">STDIO</option>
                <option value="sse">SSE</option>
              </select>
              {errors.transport && (
                <p className="text-red-500 text-sm mt-1">{errors.transport.message}</p>
              )}
            </div>

            {(transport === 'http' || transport === 'sse') && (
              <div>
                <label className="block text-sm font-medium mb-2">
                  Endpoint URL <span className="text-red-500">*</span>
                </label>
                <input
                  {...register('endpoint')}
                  type="url"
                  className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="http://localhost:8080"
                />
                {errors.endpoint && (
                  <p className="text-red-500 text-sm mt-1">{errors.endpoint.message}</p>
                )}
              </div>
            )}

            {transport === 'stdio' && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Command <span className="text-red-500">*</span>
                  </label>
                  <input
                    {...register('command')}
                    className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="/usr/bin/node"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Arguments</label>
                  <input
                    {...register('args.0')}
                    className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="server.js"
                  />
                </div>
              </>
            )}

            <div>
              <label className="block text-sm font-medium mb-2">
                Sensitivity Level <span className="text-red-500">*</span>
              </label>
              <select
                {...register('sensitivity_level')}
                className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
              <p className="text-sm text-muted-foreground mt-1">
                This determines the authorization requirements for tools in this server
              </p>
            </div>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="bg-primary text-primary-foreground px-6 py-2 rounded-md hover:bg-primary/90 transition-colors"
              >
                Next: Tools →
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Tools Configuration */}
        {step === 2 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold mb-4">Tools Configuration</h2>

            <p className="text-sm text-muted-foreground">
              Add the tools that this server provides. You can also add them later.
            </p>

            {toolFields.map((field, index) => (
              <div key={field.id} className="border rounded-md p-4 space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="font-medium">Tool #{index + 1}</h3>
                  <button
                    type="button"
                    onClick={() => removeTool(index)}
                    className="text-red-500 hover:text-red-700 text-sm"
                  >
                    Remove
                  </button>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Tool Name</label>
                  <input
                    {...register(`tools.${index}.name` as const)}
                    className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="execute_query"
                  />
                  {errors.tools?.[index]?.name && (
                    <p className="text-red-500 text-sm mt-1">
                      {errors.tools[index]?.name?.message}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Description</label>
                  <textarea
                    {...register(`tools.${index}.description` as const)}
                    className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                    rows={2}
                    placeholder="Executes SQL queries against the database"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Sensitivity Level</label>
                  <select
                    {...register(`tools.${index}.sensitivity_level` as const)}
                    className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
              </div>
            ))}

            <button
              type="button"
              onClick={() =>
                appendTool({
                  name: '',
                  description: '',
                  sensitivity_level: 'low',
                })
              }
              className="w-full border-2 border-dashed border-muted-foreground/25 rounded-md py-3 text-muted-foreground hover:border-primary hover:text-primary transition-colors"
            >
              + Add Tool
            </button>

            <div className="flex justify-between">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="px-6 py-2 border rounded-md hover:bg-muted transition-colors"
              >
                ← Back
              </button>
              <button
                type="button"
                onClick={() => setStep(3)}
                className="bg-primary text-primary-foreground px-6 py-2 rounded-md hover:bg-primary/90 transition-colors"
              >
                Next: Review →
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Review and Submit */}
        {step === 3 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold mb-4">Review & Submit</h2>

            <div className="space-y-4">
              <div className="border-b pb-4">
                <h3 className="font-medium text-sm text-muted-foreground mb-2">Server Details</h3>
                <dl className="space-y-2">
                  <div>
                    <dt className="text-sm font-medium inline">Name:</dt>
                    <dd className="inline ml-2">{watch('name')}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium inline">Transport:</dt>
                    <dd className="inline ml-2">{watch('transport')}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium inline">Sensitivity:</dt>
                    <dd className="inline ml-2">{watch('sensitivity_level')}</dd>
                  </div>
                </dl>
              </div>

              {toolFields.length > 0 && (
                <div>
                  <h3 className="font-medium text-sm text-muted-foreground mb-2">
                    Tools ({toolFields.length})
                  </h3>
                  <ul className="space-y-1">
                    {toolFields.map((_, index) => (
                      <li key={index} className="text-sm">
                        • {watch(`tools.${index}.name`)} ({watch(`tools.${index}.sensitivity_level`)})
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="bg-muted/50 p-4 rounded-md">
              <p className="text-sm">
                By registering this server, you confirm that it complies with your organization's
                security policies and has appropriate authorization controls.
              </p>
            </div>

            <div className="flex justify-between">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="px-6 py-2 border rounded-md hover:bg-muted transition-colors"
              >
                ← Back
              </button>
              <button
                type="submit"
                disabled={isSubmitting || mutation.isPending}
                className="bg-primary text-primary-foreground px-6 py-2 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting || mutation.isPending ? 'Registering...' : 'Register Server'}
              </button>
            </div>
          </div>
        )}
      </form>
    </div>
  );
}
