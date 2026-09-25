import { AlertCircle } from "lucide-react";
import { cloneElement, isValidElement, useId, type ReactElement, type ReactNode } from "react";

interface FieldProps {
  label: string;
  helper?: string;
  error?: string;
  /** 单个表单控件（input/select/textarea）。 */
  children: ReactElement;
  className?: string;
}

/** 统一表单字段：label + 控件 + helper/error（aria 关联）。 */
export function Field({ label, helper, error, children, className }: FieldProps) {
  const id = useId();
  const helperId = `${id}-helper`;
  const errorId = `${id}-error`;
  const describedBy = [error ? errorId : null, helper ? helperId : null].filter(Boolean).join(" ") || undefined;

  let control: ReactNode = children;
  if (isValidElement(children)) {
    control = cloneElement(children as ReactElement<Record<string, unknown>>, {
      id,
      "aria-invalid": error ? true : undefined,
      "aria-describedby": describedBy,
    });
  }

  return (
    <div className={["field", className ?? ""].filter(Boolean).join(" ")}>
      <label className="field__label" htmlFor={id}>{label}</label>
      {control}
      {error ? (
        <p className="field__error" id={errorId} role="alert">
          <AlertCircle size={13} aria-hidden="true" />
          <span>{error}</span>
        </p>
      ) : null}
      {helper ? <p className="field__helper" id={helperId}>{helper}</p> : null}
    </div>
  );
}
