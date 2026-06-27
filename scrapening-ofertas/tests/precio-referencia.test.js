import {
    normalizarProductosCencosud,
    normalizarProductosTottus,
    normalizarProductosUnimarc,
    normalizarProductosLider,
    extraerListaProductosVtex,
    normalizarProductosVtex,
    mejorPrecio,
    SUPERMERCADOS,
} from '../src/precio-referencia.js';

// ─── Fixtures basados en respuestas REALES capturadas ────────────────────────

// Cencosud BFF (https://bff.jumbo.cl/catalog/plp) — estructura real jun 2026.
function cencosudJson() {
    return {
        products: [
            {
                productId: 498,
                brand: 'Coca-Cola',
                slug: 'bebida-cocacola-zero-15-l-botella-desechable',
                items: [
                    {
                        skuId: '500',
                        name: 'Bebida Coca-Cola Zero 1.5 L',
                        price: 2290,
                        listPrice: 2290,
                        ppumPrice: 1527,
                        measurementUnitUn: 'lt',
                        stock: true,
                        images: ['https://x/coca-zero.jpg'],
                        promotions: [
                            { name: 'OFERTA 2X2990', type: 'mx', value: 2990, unitPrice: 1495, mQuantity: 2 },
                        ],
                    },
                ],
            },
            {
                productId: 389,
                brand: 'Coca-Cola',
                slug: 'bebida-cocacola-original-2l',
                items: [
                    {
                        skuId: '391',
                        name: 'Bebida Coca-Cola Original 2 L',
                        price: 2490,
                        listPrice: 2990,
                        ppumPrice: 1245,
                        measurementUnitUn: 'lt',
                        stock: true,
                        images: [],
                        promotions: [],
                    },
                ],
            },
            // sin precio → debe descartarse
            { productId: 1, brand: 'X', slug: 'x', items: [{ skuId: '2', name: 'X', stock: true }] },
        ],
    };
}

describe('normalizarProductosCencosud', () => {
    test('descarta productos sin precio', () => {
        expect(normalizarProductosCencosud(cencosudJson())).toHaveLength(2);
    });

    test('mapea precio, marca, disponibilidad y precio/unidad', () => {
        const [p] = normalizarProductosCencosud(cencosudJson());
        expect(p).toMatchObject({
            nombre: 'Bebida Coca-Cola Zero 1.5 L',
            marca: 'Coca-Cola',
            precio: 2290,
            disponible: true,
            precioPorUnidad: 1527,
            unidadMedida: 'lt',
            sku: '500',
        });
    });

    test('calcula ahorroPct cuando listPrice > price', () => {
        const prods = normalizarProductosCencosud(cencosudJson());
        const original = prods.find((p) => p.nombre.includes('Original'));
        // (2990-2490)/2990 ≈ 17%
        expect(original.ahorroPct).toBe(17);
    });

    test('extrae la promoción (ej. 2x$2990)', () => {
        const [p] = normalizarProductosCencosud(cencosudJson());
        expect(p.promo).toMatchObject({ precio: 2990, precioUnitario: 1495, cantidad: 2 });
    });

    test('sin promoción → promo null', () => {
        const prods = normalizarProductosCencosud(cencosudJson());
        const original = prods.find((p) => p.nombre.includes('Original'));
        expect(original.promo).toBeNull();
    });

    test('json vacío/basura → []', () => {
        expect(normalizarProductosCencosud(null)).toEqual([]);
        expect(normalizarProductosCencosud({})).toEqual([]);
    });
});

// Tottus (__NEXT_DATA__ → props.pageProps.results) — estructura real jun 2026.
function tottusJson() {
    return {
        props: {
            pageProps: {
                results: [
                    {
                        productId: 111,
                        skuId: 222,
                        displayName: 'Bebida Coca-Cola Original 1.5 L',
                        brand: 'Coca-Cola',
                        url: 'https://tottus.falabella.com/tottus-cl/product/111/x',
                        mediaUrls: ['https://x/coca.jpg'],
                        prices: [
                            {
                                type: 'internetPrice',
                                crossed: false,
                                symbol: '$ ',
                                price: ['1.890'],
                                pum: { label: 'LT', type: 'pum', symbol: '$ ', price: ['1.260'] },
                            },
                            { type: 'normalPrice', crossed: true, symbol: '$ ', price: ['2.290'] },
                        ],
                    },
                    {
                        productId: 333,
                        skuId: 444,
                        displayName: 'Agua Benedictino 1.6 L',
                        brand: 'Benedictino',
                        url: 'https://tottus.falabella.com/tottus-cl/product/333/y',
                        mediaUrls: [],
                        prices: [{ type: 'internetPrice', crossed: false, symbol: '$ ', price: ['990'] }],
                    },
                    // sin precios → descartar
                    { productId: 9, skuId: 9, displayName: 'X', brand: '', prices: [] },
                ],
            },
        },
    };
}

describe('normalizarProductosTottus', () => {
    test('descarta productos sin precio', () => {
        expect(normalizarProductosTottus(tottusJson())).toHaveLength(2);
    });

    test('parsea precio chileno "1.890" → 1890 y usa internetPrice', () => {
        const [p] = normalizarProductosTottus(tottusJson());
        expect(p).toMatchObject({ nombre: 'Bebida Coca-Cola Original 1.5 L', precio: 1890, precioLista: 2290 });
    });

    test('calcula ahorroPct con el normalPrice tachado', () => {
        const [p] = normalizarProductosTottus(tottusJson());
        // (2290-1890)/2290 ≈ 17%
        expect(p.ahorroPct).toBe(17);
    });

    test('sin precio tachado → precioLista = precio, ahorro 0', () => {
        const prods = normalizarProductosTottus(tottusJson());
        const agua = prods.find((p) => p.nombre.includes('Agua'));
        expect(agua).toMatchObject({ precio: 990, precioLista: 990, ahorroPct: 0 });
    });

    test('conserva la URL del producto', () => {
        const [p] = normalizarProductosTottus(tottusJson());
        expect(p.url).toContain('/product/111/');
    });

    test('extrae precio/unidad desde pum (supermercado)', () => {
        const [p] = normalizarProductosTottus(tottusJson());
        expect(p).toMatchObject({ precioPorUnidad: 1260, unidadMedida: 'LT' });
    });

    test('json sin results → []', () => {
        expect(normalizarProductosTottus({})).toEqual([]);
        expect(normalizarProductosTottus(null)).toEqual([]);
    });
});

// Unimarc (bff-unimarc-ecommerce → catalog/product/search) — estructura real.
function unimarcJson() {
    return {
        availableProducts: [
            {
                price: { price: '$1.350', listPrice: '$1.690', ppum: '$2.284 x litro', availableQuantity: 10000 },
                promotion: {
                    hasSavings: true,
                    type: 'mx$',
                    descriptionMessage: '2 x $1.990',
                    price: 995,
                    itemsRequiredForPromotion: 2,
                },
                item: { sku: '3819', nameComplete: 'Bebida Coca Cola original 591 ml', brand: 'Coca Cola' },
            },
            {
                price: { price: '$1.690', listPrice: '$1.690', ppum: '$1.690 x litro', availableQuantity: 10000 },
                promotion: { hasSavings: false },
                item: { sku: '3820', nameComplete: 'Bebida Coca Cola original 1 L', brand: 'Coca Cola' },
            },
        ],
        notAvailableProducts: [
            {
                price: { price: '$2.000', listPrice: '$2.000', ppum: '', availableQuantity: 0 },
                item: { sku: '9', nameComplete: 'Agotado', brand: 'X' },
            },
        ],
    };
}

describe('normalizarProductosUnimarc', () => {
    test('incluye disponibles y no disponibles', () => {
        const prods = normalizarProductosUnimarc(unimarcJson());
        expect(prods).toHaveLength(3);
        expect(prods.find((p) => p.nombre === 'Agotado').disponible).toBe(false);
    });

    test('parsea precios "$1.350"→1350 y calcula ahorroPct', () => {
        const [p] = normalizarProductosUnimarc(unimarcJson());
        expect(p).toMatchObject({ precio: 1350, precioLista: 1690 });
        expect(p.ahorroPct).toBe(20); // (1690-1350)/1690 ≈ 20%
    });

    test('extrae precio/unidad desde ppum "$2.284 x litro"', () => {
        const [p] = normalizarProductosUnimarc(unimarcJson());
        expect(p).toMatchObject({ precioPorUnidad: 2284, unidadMedida: 'litro' });
    });

    test('extrae promoción "2 x $1.990"', () => {
        const [p] = normalizarProductosUnimarc(unimarcJson());
        expect(p.promo).toMatchObject({ descripcion: '2 x $1.990', cantidad: 2 });
    });

    test('json vacío → []', () => {
        expect(normalizarProductosUnimarc({})).toEqual([]);
        expect(normalizarProductosUnimarc(null)).toEqual([]);
    });
});

// Líder (orchestra/graphql/search → itemStacks[].itemsV2) — estructura real.
function liderJson() {
    return {
        data: {
            search: {
                searchResult: {
                    itemStacks: [
                        {
                            itemsV2: [
                                {
                                    name: 'Bebida Sin Azúcar Botella, 2 L',
                                    brand: 'Coca-cola',
                                    usItemId: '00780161030528',
                                    canonicalUrl: '/ip/bebidas/00780161030528',
                                    availabilityStatusV2: { display: 'In stock', value: 'IN_STOCK' },
                                    imageInfo: { thumbnailUrl: 'https://i5.walmartimages.cl/x.jpeg' },
                                    priceInfo: {
                                        currentPrice: { price: 2000, priceString: '$2.000' },
                                        wasPrice: { price: 2500, priceString: '$2.500' },
                                        unitPrice: { priceString: '$1.000 x lt' },
                                    },
                                },
                                {
                                    name: 'Bebida Original Botella, 3 L',
                                    brand: 'Coca-cola',
                                    usItemId: '999',
                                    availabilityStatusV2: { value: 'OUT_OF_STOCK' },
                                    priceInfo: { currentPrice: { price: 3190, priceString: '$3.190' } },
                                },
                            ],
                        },
                    ],
                },
            },
        },
    };
}

describe('normalizarProductosLider', () => {
    test('aplana itemStacks → itemsV2', () => {
        expect(normalizarProductosLider(liderJson())).toHaveLength(2);
    });

    test('lee currentPrice.price y wasPrice → ahorroPct', () => {
        const [p] = normalizarProductosLider(liderJson());
        expect(p).toMatchObject({ precio: 2000, precioLista: 2500, marca: 'Coca-cola' });
        expect(p.ahorroPct).toBe(20); // (2500-2000)/2500
    });

    test('parsea precio/unidad desde "$1.000 x lt"', () => {
        const [p] = normalizarProductosLider(liderJson());
        expect(p).toMatchObject({ precioPorUnidad: 1000, unidadMedida: 'lt' });
    });

    test('disponible según availabilityStatusV2', () => {
        const prods = normalizarProductosLider(liderJson());
        expect(prods[0].disponible).toBe(true);
        expect(prods[1].disponible).toBe(false);
    });

    test('json sin itemStacks → []', () => {
        expect(normalizarProductosLider({})).toEqual([]);
        expect(normalizarProductosLider(null)).toEqual([]);
    });
});

describe('normalizarProductosVtex (helper genérico)', () => {
    const vtexProd = {
        productName: 'Coca Cola 1.5L',
        brand: 'Coca-Cola',
        items: [{ sellers: [{ commertialOffer: { Price: 1990, ListPrice: 2490, AvailableQuantity: 3 } }] }],
    };

    test('acepta array, {products} y GraphQL', () => {
        expect(extraerListaProductosVtex([vtexProd])).toHaveLength(1);
        expect(extraerListaProductosVtex({ products: [vtexProd] })).toHaveLength(1);
        expect(extraerListaProductosVtex({ data: { productSearch: { products: [vtexProd] } } })).toHaveLength(1);
        expect(extraerListaProductosVtex(null)).toEqual([]);
    });

    test('normaliza al mismo shape que Cencosud', () => {
        const [p] = normalizarProductosVtex({ products: [vtexProd] });
        expect(p).toMatchObject({ nombre: 'Coca Cola 1.5L', precio: 1990, ahorroPct: 20, disponible: true });
    });
});

describe('mejorPrecio', () => {
    const productos = [
        { nombre: 'Coca Cola Zero 1.5L', marca: 'Coca-Cola', precio: 2200, disponible: true },
        { nombre: 'Coca Cola Original 1.5L', marca: 'Coca-Cola', precio: 1990, disponible: true },
        { nombre: 'Galletas surtidas', marca: 'Costa', precio: 500, disponible: true },
    ];

    test('elige por coincidencia con la query, no el más barato global', () => {
        const m = mejorPrecio(productos, 'coca cola 1.5');
        expect(m.marca).toBe('Coca-Cola');
        expect(m.precio).toBe(1990);
    });

    test('ignora tildes y mayúsculas', () => {
        const lista = [{ nombre: 'Limón de Pica', marca: '', precio: 800, disponible: true }];
        expect(mejorPrecio(lista, 'LIMON')).toMatchObject({ precio: 800 });
    });

    test('prioriza disponibilidad sobre precio', () => {
        const lista = [
            { nombre: 'Pan molde', marca: '', precio: 900, disponible: false },
            { nombre: 'Pan molde', marca: '', precio: 1200, disponible: true },
        ];
        expect(mejorPrecio(lista, 'pan molde')).toMatchObject({ precio: 1200, disponible: true });
    });

    test('null si lista vacía', () => {
        expect(mejorPrecio([], 'x')).toBeNull();
    });

    test('NO matchea por substring: "cola" no debe elegir "colador"', () => {
        const lista = [
            { nombre: 'Colador Acero 23 cm', marca: 'Casa Joven', precio: 6990, disponible: true },
            { nombre: 'Bebida Coca Cola Original 1.5 L', marca: 'Coca-Cola', precio: 1990, disponible: true },
        ];
        expect(mejorPrecio(lista, 'coca cola')).toMatchObject({ marca: 'Coca-Cola', precio: 1990 });
    });
});

describe('SUPERMERCADOS', () => {
    test('jumbo y santaisabel están soportados y matchean /catalog/plp', () => {
        expect(SUPERMERCADOS.jumbo.soportado).toBe(true);
        expect(SUPERMERCADOS.jumbo.matchApi('https://bff.jumbo.cl/catalog/plp')).toBe(true);
        expect(SUPERMERCADOS.santaisabel.matchApi('https://bff.santaisabel.cl/catalog/plp')).toBe(true);
        expect(SUPERMERCADOS.jumbo.matchApi('https://www.jumbo.cl/static/x.png')).toBe(false);
    });

    test('los 5 supermercados están soportados', () => {
        for (const k of ['jumbo', 'santaisabel', 'unimarc', 'tottus', 'lider']) {
            expect(SUPERMERCADOS[k].soportado).toBe(true);
        }
    });

    test('tottus usa www.tottus.cl (supermercado) vía nextdata + buscador', () => {
        expect(SUPERMERCADOS.tottus.metodo).toBe('nextdata');
        expect(SUPERMERCADOS.tottus.usarBuscador).toBe(true);
        expect(SUPERMERCADOS.tottus.searchUrl('pan')).toContain('www.tottus.cl/tottus-cl/buscar');
    });

    test('unimarc soportado vía BFF propio, con warmup', () => {
        expect(SUPERMERCADOS.unimarc.warmupUrl).toBeTruthy();
        expect(SUPERMERCADOS.unimarc.matchApi('https://bff-unimarc-ecommerce.unimarc.cl/catalog/product/search')).toBe(true);
    });

    test('unimarc search usa guiones para espacios', () => {
        expect(SUPERMERCADOS.unimarc.searchUrl('coca cola')).toBe('https://www.unimarc.cl/search?q=coca-cola');
    });

    test('lider: usa buscador, requiere anti-bot, matchea su graphql', () => {
        expect(SUPERMERCADOS.lider.usarBuscador).toBe(true);
        expect(SUPERMERCADOS.lider.requiereAntiBot).toBe(true);
        expect(SUPERMERCADOS.lider.matchApi('https://super.lider.cl/orchestra/graphql/search?query=x')).toBe(true);
    });

    test('searchUrl codifica el término', () => {
        expect(SUPERMERCADOS.jumbo.searchUrl('coca cola')).toBe('https://www.jumbo.cl/busqueda?ft=coca%20cola');
    });
});
