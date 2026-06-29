import type { ButtonHTMLAttributes, ReactNode } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode
  variant?: 'primary' | 'secondary' | 'danger'
}

function Button({ children, variant = 'secondary', className = '', type = 'button', ...props }: ButtonProps) {
  return (
    <button className={`button button-${variant} ${className}`} type={type} {...props}>
      {children}
    </button>
  )
}

export default Button
