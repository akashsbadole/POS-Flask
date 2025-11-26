# Restaurant POS System - Architecture Diagram

## System Architecture Overview

```mermaid
graph TB
    subgraph "Frontend Layer"
        A[Web Interface] --> B[Mobile App]
        A --> C[Tablet POS]
        B --> D[Service Worker]
        C --> D
    end
    
    subgraph "API Gateway"
        E[Flask Application]
        F[Authentication Middleware]
        G[Role-based Access Control]
        E --> F
        F --> G
    end
    
    subgraph "Business Logic Layer"
        H[Order Management]
        I[Menu Management]
        J[Inventory Management]
        K[Recipe Management]
        L[Accounting Module]
        M[Reporting System]
        N[Subscription Management]
        O[License Management]
        P[GST Calculation]
    end
    
    subgraph "Data Layer"
        Q[PostgreSQL Database]
        R[Redis Cache]
        S[File Storage]
    end
    
    subgraph "External Services"
        T[Payment Gateway]
        U[Email Service]
        V[SMS Service]
        W[ESC/POS Printers]
    end
    
    A --> E
    B --> E
    C --> E
    E --> H
    E --> I
    E --> J
    E --> K
    E --> L
    E --> M
    E --> N
    E --> O
    E --> P
    H --> Q
    I --> Q
    J --> Q
    K --> Q
    L --> Q
    M --> Q
    N --> Q
    O --> Q
    P --> Q
    E --> R
    E --> S
    H --> T
    L --> U
    L --> V
    H --> W
```

## Enhanced User Role System

```mermaid
graph LR
    subgraph "Role Hierarchy"
        A[Super Admin] --> B[Restaurant Owner]
        B --> C[Manager]
        C --> D[Staff]
        D --> E[Cashier]
        D --> F[Kitchen Staff]
    end
    
    subgraph "Permissions"
        G[System Management]
        H[Restaurant Management]
        I[Operations Management]
        J[Basic Operations]
        K[Order Processing]
        L[Food Preparation]
    end
    
    A --> G
    B --> H
    C --> I
    D --> J
    E --> K
    F --> L
```

## Database Schema Relationships

```mermaid
erDiagram
    RESTAURANT ||--o{ USER : has
    RESTAURANT ||--o{ ORDER : contains
    RESTAURANT ||--o{ MENU_ITEM : has
    RESTAURANT ||--o{ TABLE : has
    RESTAURANT ||--o{ SUBSCRIPTION : has
    RESTAURANT ||--o{ LICENSE : requires
    RESTAURANT ||--o{ ACCOUNT : owns
    
    USER ||--o{ ORDER : creates
    USER ||--o{ TRANSACTION : performs
    
    ORDER ||--o{ ORDER_ITEM : contains
    ORDER ||--o{ PAYMENT : receives
    
    MENU_ITEM ||--o{ ORDER_ITEM : ordered_as
    MENU_ITEM ||--o{ RECIPE : has
    MENU_ITEM ||--o{ MENU_ITEM_INGREDIENT : uses
    
    RECIPE ||--o{ RECIPE_INGREDIENT : contains
    
    INGREDIENT ||--o{ MENU_ITEM_INGREDIENT : used_in
    INGREDIENT ||--o{ RECIPE_INGREDIENT : used_in
    INGREDIENT ||--o{ STOCK_ADJUSTMENT : adjusted
    
    TRANSACTION ||--o{ TRANSACTION_ENTRY : has
    TRANSACTION_ENTRY ||--|| ACCOUNT : affects
```

## GST Calculation Flow

```mermaid
flowchart TD
    A[Order Created] --> B[Calculate Subtotal]
    B --> C[Apply Discounts]
    C --> D[Calculate GST]
    D --> E[Split GST into CGST/SGST]
    E --> F[Add Service Charge]
    F --> G[Calculate Total]
    G --> H[Generate Invoice]
    
    subgraph "GST Configuration"
        I[CGST Rate: 9%]
        J[SGST Rate: 9%]
        K[Total GST: 18%]
    end
    
    D --> I
    D --> J
    I --> K
    J --> K
```

## Recipe Management System

```mermaid
flowchart LR
    A[Menu Item] --> B[Recipe]
    B --> C[Ingredients]
    B --> D[Instructions]
    B --> E[Nutritional Info]
    
    C --> F[Cost Calculation]
    F --> G[Recipe Cost]
    G --> H[Menu Pricing]
    
    I[Inventory] --> C
    J[Supplier] --> I
```

## Subscription Management Flow

```mermaid
stateDiagram-v2
    [*] --> Trial
    Trial --> Active: Subscribe
    Active --> Active: Renew
    Active --> Expired: Not Renewed
    Expired --> Active: Reactivate
    Active --> Upgraded: Plan Change
    Upgraded --> Active: Confirmed
    Active --> Downgraded: Plan Change
    Downgraded --> Active: Confirmed
```

## Offline Architecture

```mermaid
graph TB
    subgraph "Client Side"
        A[Service Worker]
        B[IndexedDB]
        C[Cache API]
    end
    
    subgraph "Sync Manager"
        D[Queue Manager]
        E[Conflict Resolver]
        F[Sync Scheduler]
    end
    
    subgraph "Server Side"
        G[API Endpoints]
        H[Conflict Detection]
        I[Data Merger]
    end
    
    A --> B
    A --> C
    B --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
```

## Security Architecture

```mermaid
graph TB
    subgraph "Authentication Layer"
        A[JWT Tokens]
        B[Session Management]
        C[Multi-factor Auth]
    end
    
    subgraph "Authorization Layer"
        D[Role-based Access]
        E[Permission Checks]
        F[Resource Guards]
    end
    
    subgraph "Data Protection"
        G[Encryption at Rest]
        H[Encryption in Transit]
        I[Data Masking]
    end
    
    A --> D
    B --> D
    C --> D
    D --> G
    E --> G
    F --> G
    G --> H
    H --> I
```

## Microservices Architecture (Future Enhancement)

```mermaid
graph TB
    subgraph "API Gateway"
        A[Kong/Nginx]
    end
    
    subgraph "Core Services"
        B[User Service]
        C[Order Service]
        D[Menu Service]
        E[Payment Service]
    end
    
    subgraph "Business Services"
        F[Inventory Service]
        G[Accounting Service]
        H[Reporting Service]
        I[Notification Service]
    end
    
    subgraph "Data Layer"
        J[User Database]
        K[Order Database]
        L[Menu Database]
        M[Inventory Database]
        N[Accounting Database]
    end
    
    A --> B
    A --> C
    A --> D
    A --> E
    A --> F
    A --> G
    A --> H
    A --> I
    
    B --> J
    C --> K
    D --> L
    F --> M
    G --> N
```

## Technology Stack

```mermaid
graph TB
    subgraph "Frontend"
        A[HTML5/CSS3]
        B[JavaScript/Alpine.js]
        C[HTMX]
        D[Tailwind CSS]
    end
    
    subgraph "Backend"
        E[Python/Flask]
        F[SQLAlchemy]
        G[Flask-SocketIO]
        H[Flask-Login]
    end
    
    subgraph "Database"
        I[PostgreSQL]
        J[Redis]
    end
    
    subgraph "Infrastructure"
        K[Docker]
        L[Nginx]
        M[Gunicorn]
    end
    
    subgraph "Monitoring"
        N[Sentry]
        O[Prometheus]
        P[Grafana]
    end
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Load Balancer"
        A[Nginx/HAProxy]
    end
    
    subgraph "Application Servers"
        B[App Server 1]
        C[App Server 2]
        D[App Server 3]
    end
    
    subgraph "Database Cluster"
        E[Primary DB]
        F[Replica DB 1]
        G[Replica DB 2]
    end
    
    subgraph "Cache Layer"
        H[Redis Cluster]
    end
    
    subgraph "File Storage"
        I[MinIO/S3]
    end
    
    A --> B
    A --> C
    A --> D
    B --> E
    C --> E
    D --> E
    E --> F
    E --> G
    B --> H
    C --> H
    D --> H
    B --> I
    C --> I
    D --> I